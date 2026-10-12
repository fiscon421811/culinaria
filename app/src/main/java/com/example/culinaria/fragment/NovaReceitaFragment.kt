package com.example.culinaria.fragment

import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.os.Bundle
import android.speech.RecognizerIntent
import android.text.InputType
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ArrayAdapter
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import com.example.culinaria.ai.RecipeAiClient
import com.example.culinaria.ai.RecipeAiError
import com.example.culinaria.ai.RecipeAiRequest
import com.example.culinaria.ai.RecipeAiResponse
import com.example.culinaria.ai.SeasonalRecipeRequest
import com.example.culinaria.ai.VideoRecipeResult
import com.example.culinaria.ai.VideoRecipeSearchRequest
import com.example.culinaria.ai.VideoRecipeSearchResponse
import com.example.culinaria.billing.AiAccess
import com.example.culinaria.billing.PaywallDialog
import com.example.culinaria.databinding.FragmentNovaReceitaBinding
import com.example.culinaria.model.Categoria
import com.example.culinaria.model.Receita
import com.example.culinaria.viewmodel.AppViewModel
import com.google.gson.Gson
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.Locale

class NovaReceitaFragment : Fragment() {
    private var _binding: FragmentNovaReceitaBinding? = null
    private val binding get() = _binding!!
    private val viewModel: AppViewModel by activityViewModels()
    private var categorias: List<Categoria> = emptyList()

    private val voiceLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode != Activity.RESULT_OK) return@registerForActivityResult
        val texto = result.data
            ?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
            ?.firstOrNull()
            ?.trim()
            ?.trimEnd('.', '!', '?')
            .orEmpty()
        if (texto.isBlank()) {
            Toast.makeText(requireContext(), "Não entendi. Tente novamente.", Toast.LENGTH_SHORT).show()
        } else {
            searchVideoRecipes(texto)
        }
    }

    private fun startVoiceSearch() {
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR")
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "pt-BR")
            putExtra(RecognizerIntent.EXTRA_PROMPT, "Diga o nome da receita que procura")
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        }
        try {
            voiceLauncher.launch(intent)
        } catch (e: ActivityNotFoundException) {
            Toast.makeText(requireContext(), "Reconhecimento de voz indisponível neste dispositivo.", Toast.LENGTH_LONG).show()
        }
    }

    override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?): View {
        _binding = FragmentNovaReceitaBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        lifecycleScope.launch { viewModel.refreshCategorias() }

        viewModel.allCategorias.observe(viewLifecycleOwner) { cats ->
            categorias = cats
            binding.spinnerCategoria.adapter = ArrayAdapter(requireContext(), android.R.layout.simple_spinner_item, cats.map { "${it.codCat} - ${it.cat}" }).also {
                it.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
            }
        }
        lifecycleScope.launch { binding.etCod.setText(viewModel.getNextCod().toString()) }
        binding.etCod.isEnabled = false
        binding.btnImportLink.setOnClickListener { showImportDialog() }
        binding.btnSearchVideoRecipe.setOnClickListener { showVideoSearchDialog() }
        binding.btnSalvar.setOnClickListener { salvarReceita() }
        binding.btnLimpar.setOnClickListener { limparCampos() }
    }


    private fun showVideoSearchDialog() {
        val queryInput = EditText(requireContext()).apply {
            hint = "Ex.: lasanha de berinjela"
            inputType = InputType.TYPE_CLASS_TEXT
        }
        AlertDialog.Builder(requireContext())
            .setTitle("BUSCAR RECEITAS EM VÍDEO")
            .setMessage("Pesquise vídeos públicos de receitas na internet.")
            .setView(queryInput)
            .setNegativeButton("CANCELAR", null)
            .setPositiveButton("BUSCAR") { _, _ -> searchVideoRecipes(queryInput.text.toString().trim()) }
            .show()
    }

    private fun searchVideoRecipes(query: String) {
        if (query.isBlank()) {
            Toast.makeText(requireContext(), "Digite o nome de uma receita.", Toast.LENGTH_SHORT).show()
            return
        }
        viewLifecycleOwner.lifecycleScope.launch {
            binding.btnSearchVideoRecipe.isEnabled = false
            binding.btnSearchVideoRecipe.text = "BUSCANDO VÍDEOS..."
            val result = withContext(Dispatchers.IO) {
                runCatching { RecipeAiClient.service.searchVideoRecipes(VideoRecipeSearchRequest(query)).execute() }
            }
            if (_binding == null) return@launch
            binding.btnSearchVideoRecipe.isEnabled = true
            binding.btnSearchVideoRecipe.text = "BUSCAR RECEITAS EM VÍDEO"
            result.fold(
                onSuccess = { response -> handleVideoSearchResponse(response) },
                onFailure = { showConnectionError(it) },
            )
        }
    }

    private fun handleVideoSearchResponse(response: retrofit2.Response<VideoRecipeSearchResponse>) {
        val results = response.body()?.results.orEmpty()
        if (!response.isSuccessful || results.isEmpty()) {
            Toast.makeText(requireContext(), "Nenhum vídeo de receita foi encontrado. Tente outro termo.", Toast.LENGTH_LONG).show()
            return
        }
        val choices = LinearLayout(requireContext()).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(20), 0, dp(20), 0)
        }
        lateinit var dialog: AlertDialog
        results.forEach { video ->
            choices.addView(com.google.android.material.button.MaterialButton(requireContext()).apply {
                text = video.title
                isAllCaps = false
                setOnClickListener {
                    dialog.dismiss()
                    generateRecipeFromVideo(video)
                }
            })
        }
        dialog = AlertDialog.Builder(requireContext())
            .setTitle("ESCOLHA UM VÍDEO")
            .setMessage("A IA criará a receita completa e manterá o link do vídeo.")
            .setView(choices)
            .setNegativeButton("CANCELAR", null)
            .create()
        dialog.show()
    }

    private fun generateRecipeFromVideo(video: VideoRecipeResult) {
        if (!AiAccess.ensureAllowed(this)) return
        viewLifecycleOwner.lifecycleScope.launch {
            binding.btnSearchVideoRecipe.isEnabled = false
            binding.btnSearchVideoRecipe.text = "CRIANDO RECEITA..."
            val result = withContext(Dispatchers.IO) {
                runCatching {
                    RecipeAiClient.service.generateSeasonalRecipe(
                        SeasonalRecipeRequest(video.title, "Receita em vídeo", "Receita encontrada na internet", "Seleção do usuário", video.url),
                    ).execute()
                }
            }
            if (_binding == null) return@launch
            binding.btnSearchVideoRecipe.isEnabled = true
            binding.btnSearchVideoRecipe.text = "BUSCAR RECEITAS EM VÍDEO"
            result.fold(
                onSuccess = { response -> handleAiResponse(response, video.url) },
                onFailure = { showConnectionError(it) },
            )
        }
    }
    private fun showImportDialog() {
        val linkInput = EditText(requireContext()).apply {
            hint = "Cole o link de uma receita, site ou vídeo"
            inputType = InputType.TYPE_TEXT_VARIATION_URI
        }
        val contextInput = EditText(requireContext()).apply {
            hint = "Legenda ou transcrição (opcional)"
            minLines = 3
            gravity = Gravity.TOP
        }
        lateinit var dialog: AlertDialog
        val voiceButton = com.google.android.material.button.MaterialButton(
            requireContext(), null, com.google.android.material.R.attr.materialButtonOutlinedStyle
        ).apply {
            text = "🎤 BUSCAR RECEITA POR VOZ"
            setOnClickListener {
                dialog.dismiss()
                startVoiceSearch()
            }
        }
        val container = LinearLayout(requireContext()).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(24), dp(4), dp(24), 0)
            addView(voiceButton)
            addView(linkInput)
            addView(contextInput)
        }
        dialog = AlertDialog.Builder(requireContext())
            .setTitle("IMPORTAR RECEITA COM IA")
            .setMessage("Cole um link ou fale o nome da receita. A IA extrai ingredientes e modo de preparo. Revise os campos antes de salvar.\n\n${AiAccess.statusText(requireContext())}")
            .setView(container)
            .setNegativeButton("CANCELAR", null)
            .setNeutralButton("⭐ PREMIUM") { _, _ -> PaywallDialog.show(requireActivity()) }
            .setPositiveButton("IMPORTAR") { _, _ -> extractRecipe(linkInput.text.toString().trim(), contextInput.text.toString().trim()) }
            .create()
        dialog.show()
    }

    private fun extractRecipe(url: String, context: String) {
        if (url.isBlank()) {
            Toast.makeText(requireContext(), "Cole um link para continuar.", Toast.LENGTH_SHORT).show()
            return
        }
        if (!AiAccess.ensureAllowed(this)) return
        viewLifecycleOwner.lifecycleScope.launch {
            binding.btnImportLink.isEnabled = false
            binding.btnImportLink.text = "IMPORTANDO..."
            val result = withContext(Dispatchers.IO) {
                runCatching { RecipeAiClient.service.extractRecipe(RecipeAiRequest(url, context.ifBlank { null })).execute() }
            }
            if (_binding == null) return@launch
            binding.btnImportLink.isEnabled = true
            binding.btnImportLink.text = "IMPORTAR RECEITA COM IA"
            result.fold(
                onSuccess = { response -> handleAiResponse(response, url) },
                onFailure = { showConnectionError(it) },
            )
        }
    }

    private fun handleAiResponse(response: retrofit2.Response<RecipeAiResponse>, url: String) {
        val recipe = response.body()
        if (!response.isSuccessful || recipe == null) {
            val message = response.errorBody()?.string()?.let { body -> runCatching { Gson().fromJson(body, RecipeAiError::class.java).error }.getOrNull() }
                ?: "Não foi possível ler esse link público."
            Toast.makeText(requireContext(), message, Toast.LENGTH_LONG).show()
            return
        }
        binding.etTitulo.setText(recipe.titulo.uppercase(Locale("pt", "BR")))
        binding.etReceita.setText(buildString {
            append("INGREDIENTES\n")
            append(recipe.ingredientes.joinToString("\n") { "• ${it.quantidade} ${it.nome}" })
            recipe.modoPreparo?.trim()?.takeIf { it.isNotEmpty() }?.let {
                append("\n\nMODO DE PREPARO\n")
                append(it)
            }
        })
        binding.etLink.setText(url)
        AiAccess.registerSuccess(requireContext())
        Toast.makeText(requireContext(), "Receita importada. Escolha a categoria e salve.", Toast.LENGTH_LONG).show()
    }

    private fun salvarReceita() {
        if (categorias.isEmpty() || binding.spinnerCategoria.selectedItemPosition < 0) {
            Toast.makeText(requireContext(), "Selecione uma categoria", Toast.LENGTH_SHORT).show()
            return
        }
        val titulo = binding.etTitulo.text.toString().trim()
        val receita = binding.etReceita.text.toString().trim()
        if (titulo.isEmpty() || receita.isEmpty()) {
            Toast.makeText(requireContext(), "Título e modo de preparo são obrigatórios", Toast.LENGTH_SHORT).show()
            return
        }
        viewModel.insertReceita(Receita(
            cod = binding.etCod.text.toString().toInt(),
            codCat = categorias[binding.spinnerCategoria.selectedItemPosition].codCat,
            titulo = titulo,
            receita = receita,
            link = binding.etLink.text.toString().trim().ifEmpty { null },
        ))
        Toast.makeText(requireContext(), "Receita salva com sucesso!", Toast.LENGTH_SHORT).show()
        limparCampos()
    }

    private fun limparCampos() {
        binding.etTitulo.text?.clear()
        binding.etReceita.text?.clear()
        binding.etLink.text?.clear()
        lifecycleScope.launch { binding.etCod.setText(viewModel.getNextCod().toString()) }
    }

    private fun showConnectionError(error: Throwable) {
        val message = when (error) {
            is SocketTimeoutException -> "A IA demorou para responder. Tente novamente."
            is UnknownHostException -> "Sem acesso ao servidor de IA. Verifique sua conexão."
            else -> "Falha ao acessar a IA: ${error.message ?: "erro de rede"}"
        }
        Toast.makeText(requireContext(), message, Toast.LENGTH_LONG).show()
    }

    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}