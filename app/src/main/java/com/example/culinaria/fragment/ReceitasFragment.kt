package com.example.culinaria.fragment


import android.app.Activity
import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.speech.RecognizerIntent
import android.text.Editable
import android.text.TextWatcher
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AlertDialog
import com.google.android.material.textfield.TextInputEditText
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import com.example.culinaria.adapter.ReceitaAdapter
import com.example.culinaria.billing.PaywallDialog
import com.example.culinaria.databinding.DialogReceitaDetalheBinding
import com.example.culinaria.databinding.FragmentReceitasBinding
import com.example.culinaria.model.Receita
import com.example.culinaria.util.PrintHelper
import com.example.culinaria.viewmodel.AppViewModel
import java.util.Locale

class ReceitasFragment : Fragment() {

    private var _binding: FragmentReceitasBinding? = null
    private val binding get() = _binding!!
    private val viewModel: AppViewModel by activityViewModels()
    private lateinit var adapter: ReceitaAdapter

    /** Campo que receberá o texto reconhecido pela voz (título ou ingrediente). */
    private var campoVoz: TextInputEditText? = null

    private val voiceLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        if (result.resultCode == Activity.RESULT_OK) {
            val texto = result.data
                ?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)
                ?.firstOrNull()
                ?.trim()
                ?.trimEnd('.', '!', '?')
                .orEmpty()
            if (texto.isNotBlank()) {
                campoVoz?.apply {
                    setText(texto)
                    setSelection(texto.length)
                }
            } else {
                Toast.makeText(requireContext(), "Não entendi. Tente novamente.", Toast.LENGTH_SHORT).show()
            }
        }
    }

    private fun iniciarBuscaPorVoz(campo: TextInputEditText, prompt: String) {
        campoVoz = campo
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR")
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, "pt-BR")
            putExtra(RecognizerIntent.EXTRA_PROMPT, prompt)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
        }
        try {
            voiceLauncher.launch(intent)
        } catch (e: ActivityNotFoundException) {
            Toast.makeText(
                requireContext(),
                "Reconhecimento de voz indisponível neste dispositivo.",
                Toast.LENGTH_LONG
            ).show()
        }
    }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentReceitasBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        adapter = ReceitaAdapter { receita -> mostrarDetalhe(receita) }
        binding.recyclerReceitas.adapter = adapter

        viewModel.homeReceitas.observe(viewLifecycleOwner) { receitas ->
            adapter.submitList(receitas)
            binding.tvContagem.text = "${receitas.size} receita(s)"
        }

        val searchWatcher = object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                viewModel.searchHomeReceitas(binding.etSearchTitulo.text?.toString().orEmpty(), binding.etSearchIngrediente.text?.toString().orEmpty())
            }
            override fun afterTextChanged(s: Editable?) = Unit
        }
        binding.etSearchTitulo.addTextChangedListener(searchWatcher)
        binding.etSearchIngrediente.addTextChangedListener(searchWatcher)

        binding.tilTitulo.setEndIconOnClickListener {
            iniciarBuscaPorVoz(binding.etSearchTitulo, "Diga o nome da receita")
        }
        binding.tilIngrediente.setEndIconOnClickListener {
            iniciarBuscaPorVoz(binding.etSearchIngrediente, "Diga um ingrediente")
        }

        binding.btnTodas.setOnClickListener {
            binding.etSearchTitulo.text?.clear()
            binding.etSearchIngrediente.text?.clear()
            viewModel.showAllReceitas()
        }

        binding.btnCategoria1.setOnClickListener {
            binding.etSearchTitulo.text?.clear()
            binding.etSearchIngrediente.text?.clear()
            viewModel.filterByCategoria(1)
        }

        binding.btnCategoria2.setOnClickListener {
            binding.etSearchTitulo.text?.clear()
            binding.etSearchIngrediente.text?.clear()
            viewModel.filterByCategoria(2)
        }

        binding.btnCategoria3.setOnClickListener {
            binding.etSearchTitulo.text?.clear()
            binding.etSearchIngrediente.text?.clear()
            viewModel.filterByCategoria(3)
        }

        binding.btnCategoria4.setOnClickListener {
            binding.etSearchTitulo.text?.clear()
            binding.etSearchIngrediente.text?.clear()
            viewModel.filterByCategoria(4)
        }

        binding.btnPremium.setOnClickListener { PaywallDialog.show(requireActivity()) }

        binding.btnImprimirLista.setOnClickListener {
            val receitas = viewModel.homeReceitas.value ?: emptyList()
            if (receitas.isEmpty()) return@setOnClickListener
            val titulo = "Livro de Receitas"
            PrintHelper.imprimirLista(requireContext(), receitas, titulo)
        }
    }

    private fun mostrarDetalhe(receita: Receita) {
        val dialogBinding = DialogReceitaDetalheBinding.inflate(layoutInflater)

        dialogBinding.tvDialogTitulo.text = receita.titulo
        dialogBinding.tvDialogCod.text = "Cód. ${receita.cod.toString().padStart(3, '0')}"

        val nomeCategoria = viewModel.allCategorias.value
            ?.firstOrNull { it.codCat == receita.codCat }?.cat
            ?: "Categoria ${receita.codCat}"
        dialogBinding.tvDialogCat.text = nomeCategoria
        dialogBinding.tvDialogReceita.text = receita.receita

        if (!receita.link.isNullOrBlank()) {
            dialogBinding.btnDialogLink.visibility = View.VISIBLE
        }

        val dialog = AlertDialog.Builder(requireContext())
            .setView(dialogBinding.root)
            .create()

        dialogBinding.btnDialogFechar.setOnClickListener { dialog.dismiss() }

        dialogBinding.btnDialogLink.setOnClickListener {
            receita.link?.let {
                runCatching { startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(it))) }
            }
        }

        dialogBinding.btnDialogCompartilhar.setOnClickListener {
            startActivity(
                Intent.createChooser(
                    Intent(Intent.ACTION_SEND).apply {
                        type = "text/plain"
                        putExtra(Intent.EXTRA_SUBJECT, receita.titulo)
                        putExtra(Intent.EXTRA_TEXT, "${receita.titulo}\n\n${receita.receita}")
                    },
                    "Compartilhar receita"
                )
            )
        }

        dialogBinding.btnDialogImprimir.setOnClickListener {
            dialog.dismiss()
            PrintHelper.imprimirReceita(requireContext(), receita)
        }

        dialog.show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}