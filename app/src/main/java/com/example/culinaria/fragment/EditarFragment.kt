package com.example.culinaria.fragment


import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import com.example.culinaria.adapter.ReceitaAdapter
import com.example.culinaria.databinding.FragmentEditarBinding
import com.example.culinaria.model.Receita
import com.example.culinaria.util.PrintHelper
import com.example.culinaria.viewmodel.AppViewModel
import kotlinx.coroutines.launch

class EditarFragment : Fragment() {

    private var _binding: FragmentEditarBinding? = null
    private val binding get() = _binding!!
    private val viewModel: AppViewModel by activityViewModels()
    private lateinit var adapter: ReceitaAdapter
    private var receitaSelecionada: Receita? = null

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentEditarBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        adapter = ReceitaAdapter { receita -> carregarReceita(receita) }
        binding.recyclerEditar.adapter = adapter

        viewModel.editarReceitas.observe(viewLifecycleOwner) { receitas ->
            adapter.submitList(receitas)
            binding.tvTotalReceitas.text = "${receitas.size} receita(s)"
        }

        val searchWatcher = object : TextWatcher {
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) = Unit
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {
                viewModel.searchEditarReceitas(binding.etSearchTituloEditar.text?.toString().orEmpty(), binding.etSearchIngredienteEditar.text?.toString().orEmpty())
            }
            override fun afterTextChanged(s: Editable?) = Unit
        }
        binding.etSearchTituloEditar.addTextChangedListener(searchWatcher)
        binding.etSearchIngredienteEditar.addTextChangedListener(searchWatcher)

        binding.btnBuscarCod.setOnClickListener {
            val codText = binding.etBuscaCod.text.toString().trim()
            if (codText.isEmpty()) {
                Toast.makeText(requireContext(), "Digite o Nº", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            lifecycleScope.launch {
                val receita = viewModel.getByCod(codText.toIntOrNull() ?: return@launch)
                if (receita != null) carregarReceita(receita)
                else {
                    Toast.makeText(requireContext(), "Nº de Receita inexistente", Toast.LENGTH_SHORT).show()
                    binding.etBuscaCod.requestFocus()
                }
            }
        }

        binding.btnSalvarEditar.setOnClickListener { salvarEdicao() }
        binding.btnDeletar.setOnClickListener { confirmarExclusao() }
        binding.btnLimparEditar.setOnClickListener { limparCampos() }

        binding.btnAbrirLink.setOnClickListener {
            val url = binding.etLinkEditar.text.toString().trim()
            if (url.isNotEmpty()) runCatching {
                startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
            } else Toast.makeText(requireContext(), "Nenhum link disponível", Toast.LENGTH_SHORT).show()
        }

        binding.btnImprimirReceita.setOnClickListener {
            val atual = receitaSelecionada
            if (atual == null) {
                Toast.makeText(requireContext(), "Selecione uma receita primeiro", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            val receitaParaImprimir = atual.copy(
                titulo = binding.etTituloEditar.text.toString().trim(),
                receita = binding.etReceitaEditar.text.toString().trim(),
                link = binding.etLinkEditar.text.toString().trim().ifEmpty { null }
            )
            PrintHelper.imprimirReceita(requireContext(), receitaParaImprimir)
        }
    }

    private fun carregarReceita(receita: Receita) {
        receitaSelecionada = receita
        binding.tvCategoria.text = receita.codCat.toString()
        binding.tvCodigo.text = receita.cod.toString()
        binding.etTituloEditar.setText(receita.titulo)
        binding.etReceitaEditar.setText(receita.receita)
        binding.etLinkEditar.setText(receita.link ?: "")
        binding.layoutEdicao.visibility = View.VISIBLE
        binding.recyclerEditar.visibility = View.GONE
        binding.tvTotalReceitas.visibility = View.GONE
        Toast.makeText(requireContext(), "✅ Receita carregada", Toast.LENGTH_SHORT).show()
    }

    private fun salvarEdicao() {
        val atual = receitaSelecionada ?: run {
            Toast.makeText(requireContext(), "Receita não selecionada", Toast.LENGTH_SHORT).show()
            return
        }
        val titulo = binding.etTituloEditar.text.toString().trim()
        val receita = binding.etReceitaEditar.text.toString().trim()
        val link = binding.etLinkEditar.text.toString().trim().ifEmpty { null }

        if (titulo.isEmpty() || receita.isEmpty()) {
            Toast.makeText(requireContext(), "Título e receita são obrigatórios", Toast.LENGTH_SHORT).show()
            return
        }
        viewModel.updateReceita(atual.copy(titulo = titulo, receita = receita, link = link))
        Toast.makeText(requireContext(), "✅ Receita atualizada!", Toast.LENGTH_SHORT).show()
        limparCampos()
    }

    private fun confirmarExclusao() {
        val atual = receitaSelecionada ?: run {
            Toast.makeText(requireContext(), "Receita não selecionada", Toast.LENGTH_SHORT).show()
            return
        }
        AlertDialog.Builder(requireContext())
            .setTitle("Confirmar Exclusão")
            .setMessage("Deseja realmente DELETAR \"${atual.titulo}\"?")
            .setPositiveButton("Sim") { _, _ ->
                viewModel.deleteReceita(atual.cod)
                Toast.makeText(requireContext(), "Receita excluída.", Toast.LENGTH_SHORT).show()
                limparCampos()
            }
            .setNegativeButton("Não", null)
            .show()
    }

    private fun limparCampos() {
        receitaSelecionada = null
        binding.etSearchTituloEditar.text?.clear()
        binding.etSearchIngredienteEditar.text?.clear()
        binding.etBuscaCod.text?.clear()
        binding.etTituloEditar.text?.clear()
        binding.etReceitaEditar.text?.clear()
        binding.etLinkEditar.text?.clear()
        binding.tvCategoria.text = "—"
        binding.tvCodigo.text = "—"
        binding.layoutEdicao.visibility = View.GONE
        binding.recyclerEditar.visibility = View.VISIBLE
        binding.tvTotalReceitas.visibility = View.VISIBLE
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}