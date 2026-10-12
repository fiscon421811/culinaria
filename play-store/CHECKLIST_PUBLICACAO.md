# Checklist de publicação

## 1. Segurança do banco (fazer ANTES de tudo)
1. No painel do Turso, **revogue o token antigo** (ele estava escrito no código e nos arquivos do projeto) e gere um novo.
2. No Worker (`cloudflare-worker/`):
   ```
   npx wrangler secret put TURSO_URL          # https://receitaturso-fiscon.aws-us-east-2.turso.io
   npx wrangler secret put TURSO_AUTH_TOKEN   # o token NOVO
   npx wrangler deploy
   ```
3. O app acessa o banco pela rota `/db` do Worker (mesma URL `MEAL_AI_BASE_URL`). O Worker só aceita SELECT/INSERT/UPDATE/DELETE.
4. Se `server/.env` ou outros arquivos já foram compartilhados/enviados com chaves, troque essas chaves também.

## 2. Chave de assinatura
```
keytool -genkeypair -v -keystore culinaria-release.jks -alias culinaria -keyalg RSA -keysize 2048 -validity 10000
```
Crie `keystore.properties` na raiz do projeto (já está no .gitignore):
```
storeFile=culinaria-release.jks
storePassword=...
keyAlias=culinaria
keyPassword=...
```
Faça backup do `.jks` e das senhas fora do projeto. Perder a chave de upload dá trabalho; use "Play App Signing" ao criar o app no Console.

## 3. Gerar o pacote
Android Studio: Build > Generate Signed App Bundle > Android App Bundle > release. Teste o release (R8 ligado) em um aparelho: abra receitas, busque por voz, importe com IA, imprima.

## 4. Play Console
1. Crie o app com o ID `br.com.edsonortolan.culinaria` (troque em `app/build.gradle.kts` se quiser outro — não muda depois de publicar).
2. **Monetizar > Produtos > Assinaturas**: crie `culinaria_premium` com plano mensal (e anual). Sugestão: R$ 9,90/mês e R$ 69,90/ano, com 7 dias grátis para novos assinantes.
3. Publique o texto de `POLITICA_DE_PRIVACIDADE.md` em uma URL pública e coloque a URL na ficha da loja **e** em `PRIVACY_POLICY_URL` (arquivo `billing/PaywallDialog.kt`).
4. Preencha ficha da loja, segurança dos dados e classificação (`FICHA_DA_LOJA.md`). Adicione ícone 512x512, imagem de destaque 1024x500 e pelo menos 2 capturas de tela.
5. Teste a compra com "testadores de licença" (Console > Configurações > Testes de licença) em faixa de teste interno.
6. Contas pessoais novas: teste fechado com o mínimo de testadores por 14 dias antes da produção (confira a regra vigente).

## 5. Pendências conhecidas
- Todos os usuários compartilham o MESMO banco de receitas. Para um app público, o ideal é separar os dados por usuário (login ou ID por instalação).
- A cota gratuita de IA é local: quem limpar os dados do app recupera os usos. Para travar de verdade, valide no Worker.
- Sem limite de requisições no Worker: configure Rate Limiting/WAF no Cloudflare.
- Em Android 15+ (targetSdk 36) o app é desenhado de ponta a ponta; confira se a barra de navegação não cobre botões.
