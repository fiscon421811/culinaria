import OpenAI from "openai";

function isPublicHttpUrl(url) {
  if (!["http:", "https:"].includes(url.protocol)) return false;
  const host = url.hostname.toLowerCase();
  if (!host || host.includes(":") || host === "localhost" || host === "::1" || host.endsWith(".local") || host.endsWith(".internal")) return false;

  const ipv4 = host.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (!ipv4) return true;
  const [a, b] = ipv4.slice(1).map(Number);
  return !(a === 0 || a === 10 || a === 127 || (a === 169 && b === 254) || (a === 172 && b >= 16 && b <= 31) || (a === 192 && b === 168));
}

function decodeHtml(value) {
  const namedEntities = { nbsp: " ", aacute: "á", agrave: "à", acirc: "â", atilde: "ã", auml: "ä", ccedil: "ç", eacute: "é", egrave: "è", ecirc: "ê", euml: "ë", iacute: "í", igrave: "ì", icirc: "î", iuml: "ï", oacute: "ó", ograve: "ò", ocirc: "ô", otilde: "õ", ouml: "ö", uacute: "ú", ugrave: "ù", ucirc: "û", uuml: "ü" };
  return value
    .replace(/&#x([0-9a-f]+);/gi, (_, hex) => String.fromCodePoint(parseInt(hex, 16)))
    .replace(/&#(\d+);/g, (_, decimal) => String.fromCodePoint(parseInt(decimal, 10)))
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&([a-z]+);/gi, (match, name) => namedEntities[name.toLowerCase()] || match);
}

function getMetaContent(html) {
  const preferredNames = new Set(["description", "og:description", "twitter:description", "og:title", "twitter:title"]);
  return [...html.matchAll(/<meta\b[^>]*>/gi)]
    .map((match) => match[0])
    .map((tag) => {
      const key = tag.match(/\b(?:name|property)=["']([^"']+)["']/i)?.[1]?.toLowerCase();
      const content = tag.match(/\bcontent=["']([^"']*)["']/i)?.[1];
      return key && content && preferredNames.has(key) ? content : "";
    })
    .filter(Boolean);
}

function getJsonLd(html) {
  return [...html.matchAll(/<script\b[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi)]
    .map((match) => match[1].trim())
    .filter(Boolean)
    .join("\n");
}

function extractRecipeInstructions(html) {
  const scripts = [...html.matchAll(/<script\b[^>]*type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi)]
    .map((match) => match[1].trim())
    .filter(Boolean);

  const findRecipe = (value) => {
    if (Array.isArray(value)) {
      for (const entry of value) {
        const recipe = findRecipe(entry);
        if (recipe) return recipe;
      }
      return null;
    }
    if (!value || typeof value !== "object") return null;
    const types = Array.isArray(value["@type"]) ? value["@type"] : [value["@type"]];
    if (types.some((type) => String(type).toLowerCase() === "recipe")) return value;
    for (const entry of Object.values(value)) {
      const recipe = findRecipe(entry);
      if (recipe) return recipe;
    }
    return null;
  };

  const formatSteps = (value) => {
    if (typeof value === "string") return decodeHtml(value).trim();
    if (Array.isArray(value)) return value.map(formatSteps).filter(Boolean).join("\n");
    if (!value || typeof value !== "object") return "";
    return formatSteps(value.text || value.name || value.itemListElement);
  };

  for (const raw of scripts) {
    try {
      const recipe = findRecipe(JSON.parse(raw));
      const steps = formatSteps(recipe?.recipeInstructions);
      if (steps) return steps;
    } catch {
      // Ignora dados estruturados inválidos e tenta o próximo bloco.
    }
  }
  return "";
}

async function fetchPublicDescription(url) {
  const source = new URL(url);
  const candidates = [source.href];
  if (source.hostname.endsWith("instagram.com")) {
    const embed = new URL(source.href);
    embed.search = "";
    embed.pathname = `${embed.pathname.replace(/\/$/, "")}/embed/captioned/`;
    candidates.push(embed.href);
  }

  for (const candidate of candidates) {
    try {
      let candidateUrl = new URL(candidate);
      let response;
      for (let redirects = 0; redirects <= 3; redirects += 1) {
        response = await fetch(candidateUrl, {
          headers: {
            "User-Agent": "Mozilla/5.0 (compatible; CulinariaMealPlanner/1.0)",
            "Accept-Language": "pt-BR,pt;q=0.9",
          },
          redirect: "manual",
        });
        if (response.status < 300 || response.status >= 400) break;
        const location = response.headers.get("location");
        if (!location) break;
        candidateUrl = new URL(location, candidateUrl);
        if (!isPublicHttpUrl(candidateUrl)) {
          response = null;
          break;
        }
      }
      if (!response?.ok) continue;
      const contentType = response.headers.get("content-type") || "";
      if (!contentType.includes("text/html") && !contentType.includes("application/xhtml+xml")) continue;
      const html = (await response.text()).slice(0, 250_000);
      const caption = html.match(/<div class="Caption">([\s\S]*?)<\/div>/i)?.[1]
        ?.replace(/<br\s*\/?\s*>/gi, "\n")
        .replace(/<[^>]+>/g, " ");
      const text = [...getMetaContent(html), caption || "", getJsonLd(html)].filter(Boolean).join("\n");
      const modoPreparo = extractRecipeInstructions(html);
      if (text || modoPreparo) {
        return {
          text: decodeHtml(text).replace(/\s+\n/g, "\n").trim().slice(0, 18_000),
          modoPreparo,
        };
      }
    } catch {
      // Tenta outra representacao publica da pagina.
    }
  }
  return { text: "", modoPreparo: "" };
}

async function createGroqRecipe(apiKey, prompt) {
  const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model: "openai/gpt-oss-20b",
      messages: [
        {
          role: "system",
          content: "Responda exclusivamente JSON RFC 8259 valido, sem markdown. Use aspas duplas em todas as chaves e textos, no formato {\"titulo\":\"texto\",\"ingredientes\":[{\"nome\":\"texto\",\"quantidade\":\"texto\"}],\"modoPreparo\":\"texto\"}. Escreva todos os valores em portugues brasileiro correto, com ortografia, acentuacao e concordancia revisadas; nao use ingles nem abreviacoes informais.",
        },
        { role: "user", content: prompt },
      ],
      response_format: { type: "json_object" },
      temperature: 0.1,
    }),
  });
  if (!response.ok) {
    const detail = await response.text();
    const error = new Error(`Groq: ${detail.slice(0, 300)}`);
    error.status = response.status;
    throw error;
  }
  const data = await response.json();
  const content = data.choices?.[0]?.message?.content;
  return typeof content === "string" ? content : JSON.stringify(content);
}

function parseRecipeOutput(output) {
  let text = String(output)
    .trim()
    .replace(/^```(?:json)?\s*/i, "")
    .replace(/\s*```$/, "")
    .replace(/^\{\s*\{+/, "{")
    .replace(/\}+\s*$/, "}");
  const firstBrace = text.indexOf("{");
  const lastBrace = text.lastIndexOf("}");
  if (firstBrace >= 0 && lastBrace > firstBrace) text = text.slice(firstBrace, lastBrace + 1);
  try {
    return JSON.parse(text);
  } catch {
    const normalized = text
      .replace(/([{,]\s*)'([^']+)'\s*:/g, '$1"$2":')
      .replace(/([{,]\s*)([A-Za-z_][\w-]*)\s*:/g, '$1"$2":')
      .replace(/:\s*'([^']*)'/g, (_, value) => `:${JSON.stringify(value)}`);
    try {
      return JSON.parse(normalized);
    } catch {
      const title = text.match(/["']?titulo["']?\s*:\s*["']?([^,"'\n}]+)/i)?.[1]?.trim();
      const ingredients = [...text.matchAll(
        /["']?nome["']?\s*:\s*["']?([^,"'\n}]+)["']?[\s\S]{0,180}?["']?quantidade["']?\s*:\s*["']?([^,"'\n}]+)/gi,
      )].map((match) => ({ nome: match[1].trim(), quantidade: match[2].trim() }));
      if (title && ingredients.length) return { titulo: title, ingredientes, modoPreparo: "" };
      throw new Error("A Groq retornou uma estrutura de receita invalida.");
    }
  }
}



async function searchYoutubeRecipeVideos(query) {
  try {
    const response = await fetch("https://www.youtube.com/results?search_query=" + encodeURIComponent(query + " receita"), {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; CulinariaMealPlanner/1.0)" },
    });
    if (!response.ok) return [];
    const html = (await response.text()).slice(0, 1_000_000);
    const results = [];
    const seen = new Set();
    const pattern = /"videoId":"([A-Za-z0-9_-]{11})"[\s\S]{0,2400}?"title":\{"runs":\[\{"text":"((?:\\.|[^"\\])*)"/g;
    for (const match of html.matchAll(pattern)) {
      const videoId = match[1];
      if (seen.has(videoId)) continue;
      seen.add(videoId);
      const title = decodeHtml(match[2].replace(/\\u0026/g, "&").replace(/\\"/g, '"')).trim();
      if (title) results.push({ title, url: "https://www.youtube.com/watch?v=" + videoId });
      if (results.length === 6) break;
    }
    return results;
  } catch {
    return [];
  }
}

async function searchVideoRecipes(body) {
  const query = typeof body?.query === "string" ? body.query.trim().slice(0, 120) : "";
  if (!query) return Response.json({ error: "Informe o nome da receita para buscar vídeos." }, { status: 400, headers: corsHeaders });
  return Response.json({ results: await searchYoutubeRecipeVideos(query) }, { headers: corsHeaders });
}
async function findRecipeVideo(title) {
  try {
    const query = encodeURIComponent(`${title} receita`);
    const response = await fetch(`https://www.youtube.com/results?search_query=${query}`, {
      headers: { "User-Agent": "Mozilla/5.0 (compatible; CulinariaMealPlanner/1.0)" },
    });
    if (!response.ok) return null;
    const html = (await response.text()).slice(0, 1_000_000);
    const videoId = html.match(/"videoId":"([A-Za-z0-9_-]{11})"/)?.[1];
    return videoId ? `https://www.youtube.com/watch?v=${videoId}` : null;
  } catch {
    return null;
  }
}
async function generateSeasonalRecipe(env, body) {
  const title = typeof body?.title === "string" ? body.title.trim().slice(0, 160) : "";
  const season = typeof body?.season === "string" ? body.season.trim().slice(0, 60) : "";
  const meal = typeof body?.meal === "string" ? body.meal.trim().slice(0, 80) : "";
  const day = typeof body?.day === "string" ? body.day.trim().slice(0, 40) : "";
  const selectedVideoUrl = typeof body?.videoUrl === "string" ? body.videoUrl.trim().slice(0, 500) : "";
  if (!title || !season || !meal || !day) {
    return Response.json({ error: "Dados insuficientes para gerar a receita sazonal." }, { status: 400, headers: corsHeaders });
  }

  const usingGroq = Boolean(env.GROQ_API_KEY);
  if (!usingGroq && !env.OPENAI_API_KEY) {
    return Response.json({ error: "Configure o segredo GROQ_API_KEY no Worker para usar a IA." }, { status: 500, headers: corsHeaders });
  }

  try {
    const prompt = `Crie uma receita brasileira completa e viável para o prato sugerido abaixo. A receita será salva no livro da pessoa usuária, portanto não use marcadores como "a definir" nem peça que ela complete informações.
Prato: ${title}
Estação no Hemisfério Sul: ${season}
Refeição: ${meal}
Dia sugerido: ${day}

Retorne ingredientes com quantidades realistas para 2 porções e modo de preparo em passos numerados, claro e completo. Use português brasileiro correto. Inclua ao menos 5 ingredientes e instruções de preparo seguras. O campo videoUrl deve ser null: não invente, adivinhe ou crie links de vídeos.`;
    const outputText = usingGroq
      ? await createGroqRecipe(env.GROQ_API_KEY, prompt)
      : (await new OpenAI({ apiKey: env.OPENAI_API_KEY }).responses.create({
          model: "gpt-5-mini",
          input: prompt,
          text: { format: { type: "json_schema", name: "receita_sazonal", strict: true, schema: recipeSchema } },
        })).output_text;
    if (!outputText) throw new Error("O provedor de IA não retornou uma receita estruturada.");
    const recipe = parseRecipeOutput(outputText);
    const hasUsableIngredient = recipe.ingredientes?.some((ingredient) => ingredient.nome?.trim() && ingredient.quantidade?.trim());
    if (!hasUsableIngredient || !recipe.modoPreparo?.trim()) {
      return Response.json({ error: "A IA não conseguiu gerar uma receita completa. Tente novamente." }, { status: 502, headers: corsHeaders });
    }
    const videoUrl = selectedVideoUrl || await findRecipeVideo(recipe.titulo);
    return Response.json({ ...recipe, videoUrl }, { headers: corsHeaders });
  } catch (error) {
    console.error({ message: error?.message });
    return Response.json({ error: "Não foi possível gerar a receita completa agora. Tente novamente." }, { status: 502, headers: corsHeaders });
  }
}
const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type"
};

const recipeSchema = {
  type: "object",
  additionalProperties: false,
  properties: {
    titulo: { type: "string" },
    ingredientes: {
      type: "array",
      items: {
        type: "object",
        additionalProperties: false,
        properties: { nome: { type: "string" }, quantidade: { type: "string" } },
        required: ["nome", "quantidade"]
      }
    },
    modoPreparo: { type: "string" },
    videoUrl: { type: ["string", "null"] }
  },
  required: ["titulo", "ingredientes", "modoPreparo", "videoUrl"]
};


// ---- Proxy do banco (Turso) ----------------------------------------------
// O token do Turso fica nos segredos do Worker (TURSO_URL e TURSO_AUTH_TOKEN).
// O app nunca vê o token. Só são aceitos comandos de dados (SELECT/INSERT/UPDATE/DELETE).
const ALLOWED_SQL = /^\s*(select|insert|update|delete)\b/i;
const MAX_DB_BODY = 200_000;

async function proxyDatabase(request, env) {
  if (!env.TURSO_URL || !env.TURSO_AUTH_TOKEN) {
    return Response.json({ error: "Banco não configurado no servidor." }, { status: 500, headers: corsHeaders });
  }
  const raw = await request.text();
  if (raw.length > MAX_DB_BODY) {
    return Response.json({ error: "Requisição grande demais." }, { status: 413, headers: corsHeaders });
  }
  let body;
  try {
    body = JSON.parse(raw);
  } catch {
    return Response.json({ error: "JSON inválido." }, { status: 400, headers: corsHeaders });
  }
  const requests = Array.isArray(body?.requests) ? body.requests : null;
  if (!requests || requests.length === 0 || requests.length > 20) {
    return Response.json({ error: "Requisição inválida." }, { status: 400, headers: corsHeaders });
  }
  for (const item of requests) {
    if (item?.type === "close") continue;
    const sql = item?.stmt?.sql;
    if (item?.type !== "execute" || typeof sql !== "string" || sql.length > 5000 || sql.includes(";") && sql.trim().replace(/;\s*$/, "").includes(";") || !ALLOWED_SQL.test(sql)) {
      return Response.json({ error: "Comando não permitido." }, { status: 403, headers: corsHeaders });
    }
  }
  const upstream = await fetch(new URL("/v2/pipeline", env.TURSO_URL).href, {
    method: "POST",
    headers: { "Authorization": `Bearer ${env.TURSO_AUTH_TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return new Response(await upstream.text(), {
    status: upstream.status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { headers: corsHeaders });
    const endpoint = new URL(request.url);
    if (request.method === "GET" && endpoint.pathname === "/health") return Response.json({ ok: true }, { headers: corsHeaders });
    if (request.method !== "POST" || !["/extract-recipe", "/generate-seasonal-recipe", "/search-video-recipes", "/db"].includes(endpoint.pathname)) {
      return Response.json({ error: "Rota nao encontrada." }, { status: 404, headers: corsHeaders });
    }

    if (endpoint.pathname === "/db") {
      try {
        return await proxyDatabase(request, env);
      } catch (error) {
        console.error({ message: error?.message });
        return Response.json({ error: "Falha ao acessar o banco." }, { status: 502, headers: corsHeaders });
      }
    }

    try {
      const body = await request.json();
      if (endpoint.pathname === "/search-video-recipes") return await searchVideoRecipes(body);
      if (endpoint.pathname === "/generate-seasonal-recipe") return await generateSeasonalRecipe(env, body);
      const source = new URL(body?.url);
      const context = typeof body?.context === "string" ? body.context.trim().slice(0, 12000) : "";
      if (!isPublicHttpUrl(source)) {
        return Response.json({ error: "Use um link público HTTP ou HTTPS." }, { status: 400, headers: corsHeaders });
      }
      const publicRecipe = await fetchPublicDescription(source.href);
      const usingGroq = Boolean(env.GROQ_API_KEY);
      if (!usingGroq && !env.OPENAI_API_KEY) {
        return Response.json(
          { error: "Configure o segredo GROQ_API_KEY no Worker para usar a IA." },
          { status: 500, headers: corsHeaders },
        );
      }

      const ai = new OpenAI(
        usingGroq
          ? { apiKey: env.GROQ_API_KEY, baseURL: "https://api.groq.com/openai/v1" }
          : { apiKey: env.OPENAI_API_KEY },
      );
      const prompt = `Extraia os ingredientes e o modo de preparo desta receita em português brasileiro. Revise a ortografia, a acentuação e a concordância antes de responder. Mantenha nomes de ingredientes claros e completos, sem traduções para inglês nem abreviações informais.
Link de origem: ${source.href}
Conteúdo público da página: ${publicRecipe.text || "(nao acessivel)"}\nModo de preparo encontrado nos dados estruturados: ${publicRecipe.modoPreparo || "(nao encontrado)"}
Texto, legenda ou transcrição fornecida pela pessoa usuária: ${context || "(nao fornecida)"}
Use o texto fornecido pela pessoa usuária como fonte principal quando existir; caso contrário use o conteúdo público da página, incluindo dados estruturados de receitas. Extraia somente ingredientes e etapas de preparo explicitamente identificáveis. Organize o modo de preparo em passos claros, separados por quebras de linha. Não invente ingredientes, etapas ou tempos nem responda com mensagens de bloqueio, espera ou indisponibilidade. Se não houver modo de preparo identificável, retorne uma string vazia.`;

      const outputText = usingGroq
        ? await createGroqRecipe(env.GROQ_API_KEY, prompt)
        : (await ai.responses.create({
            model: "gpt-5-mini",
            input: prompt,
            text: { format: { type: "json_schema", name: "receita_extraida", strict: true, schema: recipeSchema } },
          })).output_text;

      if (!outputText) throw new Error("O provedor de IA nao retornou uma receita estruturada para este link.");
      const recipe = parseRecipeOutput(outputText);
      if (!recipe.modoPreparo?.trim() && publicRecipe.modoPreparo) recipe.modoPreparo = publicRecipe.modoPreparo;
      const blockedTerms = /aguardando|bloquead|n[aã]o foi poss[ií]vel|indispon[ií]vel|acesso/i;
      const hasUsableIngredient = recipe.ingredientes?.some((ingredient) =>
        ingredient.nome?.trim() && !blockedTerms.test(ingredient.nome)
      );
      if (!hasUsableIngredient || blockedTerms.test(recipe.titulo || "")) {
        return Response.json(
          { error: "Não foi possível identificar ingredientes suficientes nessa página. Cole o texto, a legenda ou a transcrição para a IA analisar." },
          { status: 422, headers: corsHeaders },
        );
      }
      return Response.json(recipe, { headers: corsHeaders });
    } catch (error) {
      const status = error?.status;
      const invalidKey = status === 401;
      const rateLimited = status === 429;
      const message = invalidKey
        ? "A chave do provedor de IA foi recusada. Verifique GROQ_API_KEY (ou OPENAI_API_KEY durante a transicao)."
        : rateLimited
          ? "Limite ou credito do provedor de IA atingido. Aguarde alguns minutos e verifique sua conta Groq."
          : status
            ? `O provedor de IA retornou HTTP ${status}. Verifique chave, limite e modelo.`
            : "Não foi possível analisar este link público. Tente outro site ou cole o texto, a legenda ou a transcrição.";

      console.error({ status, message: error?.message });
      const responseStatus = invalidKey || rateLimited ? status : 502;
      return Response.json(
        { error: message },
        { status: responseStatus, headers: corsHeaders },
      );
    }
  }
};

