package com.example.culinaria.fragment

import android.graphics.Typeface
import android.os.Bundle
import android.widget.Toast
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.LinearLayout
import android.widget.TextView
import androidx.core.content.ContextCompat
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import com.example.culinaria.R
import com.example.culinaria.ai.RecipeAiClient
import com.example.culinaria.ai.RecipeAiError
import com.example.culinaria.ai.RecipeAiResponse
import com.example.culinaria.ai.SeasonalRecipeRequest
import com.example.culinaria.databinding.FragmentCardapioSemanalBinding
import com.example.culinaria.model.Categoria
import com.example.culinaria.model.Receita
import com.example.culinaria.viewmodel.AppViewModel
import com.google.android.material.button.MaterialButton
import com.google.gson.Gson
import com.google.android.material.card.MaterialCardView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.Calendar
import java.util.Locale

class CardapioSemanalFragment : Fragment() {
    private var _binding: FragmentCardapioSemanalBinding? = null
    private val binding get() = _binding!!
    private val viewModel: AppViewModel by activityViewModels()
    private var selectedMenu: Season? = null

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentCardapioSemanalBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        binding.btnMenuStyle.setOnClickListener { showMenuSelector() }
        renderSuggestion()
    }

    private fun renderSuggestion() {
        val menu = selectedMenu ?: seasonForToday(Calendar.getInstance())
        binding.tvSeason.text = "${menu.icon} ${menu.name.uppercase(portuguese)} · ${menu.period.uppercase(portuguese)}"
        binding.tvSeasonDescription.text = menu.focus
        binding.tvWeek.text = if (selectedMenu == null) "Sugestão preparada pela IA para a estação atual" else "Sugestão semanal de ${menu.name.lowercase(portuguese)}"
        binding.btnMenuStyle.text = "ALTERAR CARDÁPIO: ${menu.name.uppercase(portuguese)}"
        binding.scheduleContainer.removeAllViews()
        menu.days.forEach { binding.scheduleContainer.addView(dayCard(it)) }
    }

    private fun showMenuSelector() {
        val options = listOf(seasonalOption) + alternativeMenus
        val buttons = LinearLayout(requireContext()).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), 0, dp(20), 0)
        }
        lateinit var dialog: AlertDialog
        options.forEachIndexed { index, option ->
            buttons.addView(MaterialButton(requireContext()).apply {
                text = "${option.icon} ${option.name} — ${option.focus}"
                isAllCaps = false
                layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
                setOnClickListener {
                    selectedMenu = if (index == 0) null else option
                    dialog.dismiss()
                    renderSuggestion()
                }
            })
        }
        dialog = AlertDialog.Builder(requireContext())
            .setTitle("ESCOLHA O CARDÁPIO SEMANAL")
            .setView(buttons)
            .setNegativeButton("CANCELAR", null)
            .create()
        dialog.show()
    }    private fun dayCard(day: DayMenu) = MaterialCardView(requireContext()).apply {
        radius = dp(16).toFloat()
        cardElevation = dp(2).toFloat()
        layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
            bottomMargin = dp(10)
        }
        addView(LinearLayout(requireContext()).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(14), dp(16), dp(14))
            addView(label(day.day.uppercase(portuguese), 16, Typeface.BOLD, R.color.text_primary))
            addView(meal("🍳  Café da manhã", day.breakfast, day.day))
            addView(meal("🍛  Almoço", day.lunch, day.day))
            addView(meal("🥗  Jantar", day.dinner, day.day))
        })
    }

    private fun meal(title: String, item: String, day: String) = LinearLayout(requireContext()).apply {
        orientation = LinearLayout.VERTICAL
        setPadding(0, dp(10), 0, 0)
        addView(label("$title\n$item", 14, Typeface.NORMAL, R.color.text_secondary).apply {
            setLineSpacing(dp(2).toFloat(), 1f)
        })
        addView(MaterialButton(requireContext()).apply {
            text = "IMPORTAR PARA MINHAS RECEITAS"
            isAllCaps = false
            setPadding(0, 0, 0, 0)
            setOnClickListener { generateSuggestion(item, title, day, this@apply) }
        })
    }

    private fun generateSuggestion(title: String, meal: String, day: String, button: MaterialButton) {
        if (!com.example.culinaria.billing.AiAccess.ensureAllowed(this)) return
        button.isEnabled = false
        button.text = "GERANDO RECEITA..."
        val season = (selectedMenu ?: seasonForToday(Calendar.getInstance())).name
        viewLifecycleOwner.lifecycleScope.launch {
            val result = withContext(Dispatchers.IO) {
                runCatching { RecipeAiClient.service.generateSeasonalRecipe(SeasonalRecipeRequest(title, season, meal, day)).execute() }
            }
            if (_binding == null) return@launch
            button.isEnabled = true
            button.text = "IMPORTAR PARA MINHAS RECEITAS"
            result.fold(
                onSuccess = { response -> handleGeneratedRecipe(response, meal, day) },
                onFailure = { showGenerationError(it) },
            )
        }
    }

    private fun handleGeneratedRecipe(response: retrofit2.Response<RecipeAiResponse>, meal: String, day: String) {
        val recipe = response.body()
        if (!response.isSuccessful || recipe == null) {
            val message = response.errorBody()?.string()?.let { body -> runCatching { Gson().fromJson(body, RecipeAiError::class.java).error }.getOrNull() }
                ?: "Não foi possível gerar a receita completa."
            Toast.makeText(requireContext(), message, Toast.LENGTH_LONG).show()
            return
        }
        com.example.culinaria.billing.AiAccess.registerSuccess(requireContext())
        chooseCategoryForSuggestion(recipe, meal, day)
    }

    private fun chooseCategoryForSuggestion(recipe: RecipeAiResponse, meal: String, day: String) {
        Toast.makeText(requireContext(), "Carregando categorias...", Toast.LENGTH_SHORT).show()
        viewLifecycleOwner.lifecycleScope.launch {
            val categories = withContext(Dispatchers.IO) { viewModel.refreshCategorias() }
            if (_binding == null) return@launch
            if (categories.isEmpty()) {
                AlertDialog.Builder(requireContext())
                    .setTitle("NENHUMA CATEGORIA CADASTRADA")
                    .setMessage("A tabela de categorias não possui itens disponíveis. Cadastre uma categoria e tente importar novamente.")
                    .setPositiveButton("OK", null)
                    .show()
                return@launch
            }
            showCategoryOptions(recipe, meal, day, categories)
        }
    }

    private fun showCategoryOptions(recipe: RecipeAiResponse, meal: String, day: String, categories: List<Categoria>) {
        val options = LinearLayout(requireContext()).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), 0, dp(20), 0)
        }
        lateinit var dialog: AlertDialog
        categories.forEach { category ->
            options.addView(MaterialButton(requireContext()).apply {
                text = "${category.codCat} - ${category.cat}"
                isAllCaps = false
                layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT)
                setOnClickListener {
                    dialog.dismiss()
                    importSuggestion(recipe, meal, day, category)
                }
            })
        }
        dialog = AlertDialog.Builder(requireContext())
            .setTitle("ESCOLHA A CATEGORIA")
            .setMessage("Selecione onde salvar: ${recipe.titulo}")
            .setView(options)
            .setNegativeButton("CANCELAR", null)
            .create()
        dialog.show()
    }
    private fun importSuggestion(recipe: RecipeAiResponse, meal: String, day: String, category: Categoria) {
        if (viewModel.homeReceitas.value.orEmpty().any { it.titulo.equals(recipe.titulo, ignoreCase = true) }) {
            Toast.makeText(requireContext(), "Essa receita já está no seu Livro de Receitas.", Toast.LENGTH_LONG).show()
            return
        }
        val content = buildString {
            append("INGREDIENTES\n")
            append(recipe.ingredientes.joinToString("\n") { "• ${it.quantidade} ${it.nome}" })
            append("\n\nMODO DE PREPARO\n")
            append(recipe.modoPreparo.orEmpty())
            recipe.videoUrl?.takeIf { it.isNotBlank() }?.let { append("\n\nVÍDEO\n").append(it) }
            append("\n\nSugestão sazonal: $meal · $day")
        }
        viewLifecycleOwner.lifecycleScope.launch {
            val code = withContext(Dispatchers.IO) { viewModel.getNextCod() }
            if (_binding == null) return@launch
            viewModel.insertReceita(Receita(
                cod = code,
                codCat = category.codCat,
                titulo = recipe.titulo.uppercase(portuguese),
                receita = content,
                link = recipe.videoUrl?.takeIf { it.isNotBlank() },
            ))
            Toast.makeText(requireContext(), "Receita completa adicionada ao Livro de Receitas.", Toast.LENGTH_LONG).show()
        }
    }

    private fun showGenerationError(error: Throwable) {
        val message = when (error) {
            is SocketTimeoutException -> "A IA demorou para gerar a receita. Tente novamente."
            is UnknownHostException -> "Sem acesso ao servidor de IA. Verifique sua conexão."
            else -> "Falha ao gerar a receita: ${error.message ?: "erro de rede"}"
        }
        Toast.makeText(requireContext(), message, Toast.LENGTH_LONG).show()
    }
    private fun label(text: String, size: Int, style: Int, color: Int) = TextView(requireContext()).apply {
        this.text = text
        textSize = size.toFloat()
        setTypeface(typeface, style)
        setTextColor(ContextCompat.getColor(requireContext(), color))
    }

    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    /** Estações do Hemisfério Sul. Em 2026, o inverno vai de 21/06 a 22/09. */
    private fun seasonForToday(today: Calendar): Season {
        val monthDay = (today.get(Calendar.MONTH) + 1) * 100 + today.get(Calendar.DAY_OF_MONTH)
        return when {
            monthDay in 621..922 -> winter
            monthDay in 923..1220 -> spring
            monthDay >= 1221 || monthDay <= 320 -> summer
            else -> autumn
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }

    private data class DayMenu(val day: String, val breakfast: String, val lunch: String, val dinner: String)
    private data class Season(val name: String, val icon: String, val period: String, val focus: String, val days: List<DayMenu>)

    companion object {
        private val portuguese = Locale("pt", "BR")
        private fun menu(vararg rows: Array<String>) = rows.map { DayMenu(it[0], it[1], it[2], it[3]) }

        private val spring = Season("Primavera", "🌸", "23 de setembro a 20 de dezembro", "Cores, frescor e pratos leves com vegetais da estação.", menu(
            arrayOf("Segunda", "Vitamina de morango com aveia", "Frango grelhado com arroz de brócolis", "Salada de folhas com tiras de carne"),
            arrayOf("Terça", "Crepioca de queijo branco", "Iscas de patinho com vagem e cenoura", "Omelete de espinafre com tomate"),
            arrayOf("Quarta", "Mamão com iogurte e granola", "Filé de peixe grelhado com purê de mandioquinha", "Wrap integral de frango com rúcula"),
            arrayOf("Quinta", "Torrada com ovo mexido e chia", "Macarrão integral ao pesto com tomate-cereja", "Abobrinha recheada com ricota e frango"),
            arrayOf("Sexta", "Panqueca de banana com mel", "Sobrecoxa assada com batata-doce", "Sopa leve de legumes com peito de peru"),
            arrayOf("Sábado", "Pão de queijo de frigideira", "Risoto de limão-siciliano com filé de Saint Peter", "Salada grega com cubos de queijo e torradinhas"),
            arrayOf("Domingo", "Salada de frutas com linhaça", "Lagarto assado com farofa de cenoura", "Sanduíche natural de atum com cenoura ralada"),
        ))

        private val summer = Season("Verão", "☀️", "21 de dezembro a 20 de março", "Hidratação, pratos frios, rápidos e frutas tropicais.", menu(
            arrayOf("Segunda", "Smoothie de abacaxi com hortelã", "Salada de macarrão parafuso com atum e milho", "Crepioca de frango desfiado com requeijão"),
            arrayOf("Terça", "Iogurte batido com manga", "Peito de frango grelhado com salada de quinoa", "Omelete com tomate, cebola e manjericão"),
            arrayOf("Quarta", "Sanduíche integral de queijo e tomate", "Filé de pescada fria ao vinagrete com arroz", "Salada de grão-de-bico com lascas de bacalhau"),
            arrayOf("Quinta", "Salada de frutas com chia", "Carne moída com cubos de chuchu e arroz integral", "Wrap frio de peito de peru e creme de ricota"),
            arrayOf("Sexta", "Ovos mexidos com tomate e torrada", "Espetinho de frango com pimentão e arroz", "Tapioca de queijo-coalho com tomate"),
            arrayOf("Sábado", "Vitamina de banana com leite de coco", "Ceviche de peixe branco com chips de batata-doce", "Salada de folhas, gomos de laranja e frango"),
            arrayOf("Domingo", "Suco verde com torrada integral", "Filé de miolo de alcatra acebolado e salada", "Sanduíche de pão sírio com homus e pepino"),
        ))

        private val autumn = Season("Outono", "🍁", "21 de março a 20 de junho", "Pratos mais aconchegantes e raízes como abóbora, cará e mandioca.", menu(
            arrayOf("Segunda", "Vitamina de banana, aveia e canela", "Escondidinho de carne moída com mandioca", "Creme de abóbora cabotiá com gengibre"),
            arrayOf("Terça", "Panqueca de maçã com canela", "Sobrecoxa de frango ensopada com quiabo", "Omelete de cogumelos com torrada"),
            arrayOf("Quarta", "Pão integral na chapa com requeijão", "Carne de panela com cenoura e batata", "Caldo verde funcional com couve em tiras"),
            arrayOf("Quinta", "Ovos mexidos com queijo meia-cura", "Polenta mole com molho bolonhesa magro", "Berinjela recheada com frango gratinada"),
            arrayOf("Sexta", "Crepioca de carne-seca com nata", "Arroz integral com lentilha e filé de frango", "Sopa de feijão com macarrão paiol"),
            arrayOf("Sábado", "Bolo de caneca de cacau integral", "Strogonoff de frango com arroz e batata rústica", "Toast de abacate com ovo pochê"),
            arrayOf("Domingo", "Iogurte com mel e nozes picadas", "Assado de tiras com maionese caseira", "Tapioca de queijo com fatias de caqui"),
        ))

        private val winter = Season("Inverno", "❄️", "21 de junho a 22 de setembro", "Pratos quentes, caldos encorpados e alimentos térmicos.", menu(
            arrayOf("Segunda", "Mingau de aveia morno com canela", "Picadinho de carne com arroz e feijão-preto", "Creme de ervilha com cubos de bacon tostadinho"),
            arrayOf("Terça", "Chocolate quente funcional e torrada", "Coxa de frango assada com purê de batata", "Canja de galinha tradicional com arroz"),
            arrayOf("Quarta", "Pão de queijo de Minas quentinho", "Macarrão à bolonhesa com queijo ralado", "Sopa de goulash"),
            arrayOf("Quinta", "Ovos mexidos na manteiga com pão", "Lasanha de berinjela com carne moída", "Caldo de mandioca com costelinha desfiada"),
            arrayOf("Sexta", "Panqueca americana integral morna", "Filé de peixe assado com crosta de amêndoas", "Sopa de legumes com músculo bovino"),
            arrayOf("Sábado", "Mingau de fubá com queijo ralado", "Feijoada light com couve refogada e laranja", "Polenta frita na airfryer com carne desfiada"),
            arrayOf("Domingo", "Cappuccino caseiro e bolo de fubá", "Nhoque de batata ao molho sugo com braciola", "Sanduíche quente de forno com queijo e presunto"),
        ))
        private val seasonalOption = Season(
            "Sazonal", "🌦️", "conforme a estação", "Usa automaticamente a estação climática atual do Hemisfério Sul.", emptyList(),
        )

        private val alternativeMenus = listOf(
            Season("Vegano", "🌱", "cardápio semanal", "Refeições 100% vegetais, com grãos, legumes e proteínas vegetais.", menu(
                arrayOf("Segunda", "Overnight oats com banana", "Curry de grão-de-bico com arroz integral", "Sopa de lentilha com couve"),
                arrayOf("Terça", "Tapioca com pasta de amendoim", "Escondidinho de lentilha com mandioca", "Wrap de homus, pepino e rúcula"),
                arrayOf("Quarta", "Vitamina de manga com aveia", "Tofu grelhado com legumes e quinoa", "Macarrão integral ao molho de tomate e manjericão"),
                arrayOf("Quinta", "Pão integral com abacate", "Feijão-preto, arroz, abóbora assada e salada", "Berinjela recheada com quinoa"),
                arrayOf("Sexta", "Cuscuz com coco e frutas", "Falafel assado com tabule", "Creme de abóbora com gengibre"),
                arrayOf("Sábado", "Panqueca de banana e aveia", "Moqueca vegana de banana-da-terra", "Pizza de legumes com queijo vegetal"),
                arrayOf("Domingo", "Frutas com chia", "Lasanha de abobrinha com molho de lentilha", "Sanduíche de cogumelos e cebola caramelizada"),
            )),
            Season("Low Carb", "🥑", "cardápio semanal", "Menos carboidratos, com proteínas, vegetais e gorduras saudáveis.", menu(
                arrayOf("Segunda", "Omelete de espinafre e queijo", "Frango grelhado com brócolis e salada", "Abobrinha recheada com carne moída"),
                arrayOf("Terça", "Iogurte natural com nozes", "Salmão assado com aspargos", "Salada Caesar com frango"),
                arrayOf("Quarta", "Ovos mexidos com tomate", "Carne de panela com couve-flor", "Sopa de legumes com frango"),
                arrayOf("Quinta", "Pudim de chia com coco", "Almôndegas ao molho com abobrinha", "Omelete de cogumelos"),
                arrayOf("Sexta", "Crepioca de queijo", "Peixe grelhado com purê de couve-flor", "Salada de atum com ovos"),
                arrayOf("Sábado", "Abacate com cacau e chia", "Frango ao curry com legumes", "Hambúrguer caseiro com salada"),
                arrayOf("Domingo", "Queijo branco com frutas vermelhas", "Lombo assado com couve refogada", "Caldo de abóbora com carne desfiada"),
            )),
            Season("Brasileiro", "🇧🇷", "cardápio semanal", "Sabores regionais, ingredientes locais e preparos tradicionais brasileiros.", menu(
                arrayOf("Segunda", "Cuscuz nordestino com ovo", "Frango com quiabo, arroz e feijão", "Tapioca de queijo coalho"),
                arrayOf("Terça", "Pão de queijo com café", "Picadinho de carne, arroz, feijão e couve", "Caldo de mandioca com carne-seca"),
                arrayOf("Quarta", "Açaí com banana e granola", "Moqueca de peixe com arroz", "Omelete de legumes"),
                arrayOf("Quinta", "Bolo de fubá e leite", "Escondidinho de carne-seca com salada", "Cuscuz paulista com salada verde"),
                arrayOf("Sexta", "Tapioca de coco", "Feijoada leve com couve e laranja", "Sopa de feijão"),
                arrayOf("Sábado", "Pão na chapa com requeijão", "Galinhada com açafrão e salada", "Pastel assado de palmito"),
                arrayOf("Domingo", "Frutas tropicais", "Churrasco com vinagrete e farofa", "Sanduíche natural de frango"),
            )),
            Season("Mediterrâneo", "🫒", "cardápio semanal", "Azeite, peixes, grãos, vegetais e ervas aromáticas.", menu(
                arrayOf("Segunda", "Iogurte com frutas e nozes", "Frango mediterrâneo com quinoa", "Salada grega com grão-de-bico"),
                arrayOf("Terça", "Torrada integral com tomate", "Peixe assado com legumes e azeite", "Sopa minestrone"),
                arrayOf("Quarta", "Omelete com ervas", "Tabule com falafel assado", "Berinjela assada com ricota"),
                arrayOf("Quinta", "Aveia com figos e mel", "Macarrão integral ao pesto com tomate", "Salada de atum, feijão-branco e rúcula"),
                arrayOf("Sexta", "Pão integral com homus", "Almôndegas de peru com cuscuz marroquino", "Legumes grelhados com queijo feta"),
                arrayOf("Sábado", "Frutas, queijo e castanhas", "Risoto de limão com peixe", "Wrap de frango com tzatziki"),
                arrayOf("Domingo", "Panqueca de aveia", "Lasanha de berinjela ao molho sugo", "Salada de lentilha com ervas"),
            )),
            Season("Vegetariano", "🥕", "cardápio semanal", "Sem carnes, com ovos, laticínios, leguminosas e vegetais variados.", menu(
                arrayOf("Segunda", "Iogurte com granola", "Lentilha com arroz integral e legumes", "Omelete de espinafre com tomate"),
                arrayOf("Terça", "Tapioca com queijo branco", "Nhoque de abóbora ao molho sugo", "Salada de grão-de-bico com ricota"),
                arrayOf("Quarta", "Vitamina de banana e aveia", "Quiche de alho-poró com salada", "Sopa de legumes com queijo"),
                arrayOf("Quinta", "Pão integral com ovos", "Estrogonofe de cogumelos com arroz", "Tapioca de tomate e queijo"),
                arrayOf("Sexta", "Panqueca de maçã", "Lasanha de berinjela com ricota", "Creme de ervilha com torradas"),
                arrayOf("Sábado", "Cuscuz com queijo coalho", "Risoto de cogumelos", "Hambúrguer de grão-de-bico com salada"),
                arrayOf("Domingo", "Frutas com sementes", "Feijão-tropeiro vegetariano", "Wrap de legumes grelhados"),
            )),
        )
    }
}