import "dotenv/config";
import express from "express";
import OpenAI from "openai";

if (!process.env.OPENAI_API_KEY) throw new Error("Defina OPENAI_API_KEY no arquivo .env");

const app = express();
const client = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });
const allowedHosts = new Set(["instagram.com", "www.instagram.com", "tiktok.com", "www.tiktok.com"]);
const requestsByIp = new Map();

app.use(express.json({ limit: "32kb" }));
app.use((req, res, next) => {
  const ip = req.ip ?? "unknown";
  const now = Date.now();
  const recent = (requestsByIp.get(ip) ?? []).filter((time) => now - time < 60_000);
  if (recent.length >= 10) return res.status(429).json({ error: "Muitas tentativas. Aguarde um minuto." });
  recent.push(now); requestsByIp.set(ip, recent); next();
});

app.post("/extract-recipe", async (req, res) => {
  try {
    const url = new URL(req.body?.url);
    if (!allowedHosts.has(url.hostname)) return res.status(400).json({ error: "Use um link do Instagram ou TikTok." });

    const response = await client.responses.create({
      model: process.env.OPENAI_MODEL || "gpt-5-mini",
      tools: [{ type: "web_search" }],
      input: `Localize o conteúdo público desta publicação de receita: ${url.href}\n
Extraia os ingredientes e o modo de preparo explicitamente identificáveis. Não invente quantidades, etapas ou tempos; use "a confirmar" quando necessário. Organize o modo de preparo em passos claros separados por quebras de linha. Retorne em português brasileiro correto, revisando ortografia, acentuação e concordância; não use inglês nem abreviações informais.`,
      text: {
        format: {
          type: "json_schema", name: "receita_extraida", strict: true,
          schema: {
            type: "object", additionalProperties: false,
            properties: {
              titulo: { type: "string" },
              ingredientes: {
                type: "array", items: {
                  type: "object", additionalProperties: false,
                  properties: { nome: { type: "string" }, quantidade: { type: "string" } },
                  required: ["nome", "quantidade"]
                }
              },
              modoPreparo: { type: "string" }
            }, required: ["titulo", "ingredientes", "modoPreparo"]
          }
        }
      }
    });
    res.json(JSON.parse(response.output_text));
  } catch (error) {
    const invalidKey = error?.status === 401;
    console.error({ status: error?.status, code: error?.code, message: error?.message });
    res.status(invalidKey ? 401 : 502).json({
      error: invalidKey
        ? "A chave da OpenAI e invalida ou foi revogada. Atualize o segredo do servidor."
        : "Nao foi possivel extrair esta receita. Tente colar a legenda ou usar outro link publico."
    });
  }
});

app.get("/health", (_req, res) => res.json({ ok: true }));
app.listen(process.env.PORT || 8787, () => console.log("Servidor de IA iniciado."));

