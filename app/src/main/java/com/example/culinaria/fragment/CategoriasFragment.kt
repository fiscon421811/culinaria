package com.example.culinaria.fragment

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import com.example.culinaria.adapter.CategoriaAdapter
import com.example.culinaria.databinding.FragmentCategoriasBinding
import com.example.culinaria.model.Categoria
import com.example.culinaria.viewmodel.AppViewModel
import kotlinx.coroutines.launch

class CategoriasFragment : Fragment() {

    private var _binding: FragmentCategoriasBinding? = null
    private val binding get() = _binding!!
    private val viewModel: AppViewModel by activityViewModels()
    private lateinit var adapter: CategoriaAdapter

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        _binding = FragmentCategoriasBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)

        adapter = CategoriaAdapter(
            onDelete = { categoria -> confirmarExclusao(categoria) },
            onUpdate = { categoria -> viewModel.updateCategoria(categoria) }
        )
        binding.recyclerCategorias.adapter = adapter

        viewModel.allCategorias.observe(viewLifecycleOwner) { cats ->
            adapter.submitList(cats)
            binding.tvTotal.text = "${cats.size} categoria(s)"
        }

        binding.btnAdicionarCategoria.setOnClickListener { adicionarCategoria() }
    }

    private fun adicionarCategoria() {
        val nome = binding.etNomeCategoria.text.toString().trim()

        if (nome.isEmpty()) {
            Toast.makeText(requireContext(), "Digite o nome da Categoria", Toast.LENGTH_SHORT).show()
            binding.etNomeCategoria.requestFocus()
            return
        }

        lifecycleScope.launch {
            val proximoCod = viewModel.getNextCodCat()
            val novaCategoria = Categoria(codCat = proximoCod, cat = nome)
            viewModel.insertCategoria(novaCategoria)
            binding.etNomeCategoria.text?.clear()
            Toast.makeText(requireContext(), "✅ Categoria adicionada!", Toast.LENGTH_SHORT).show()
        }
    }

    private fun confirmarExclusao(categoria: Categoria) {
        AlertDialog.Builder(requireContext())
            .setTitle("Confirmar Exclusão")
            .setMessage("Deseja realmente DELETAR a categoria \"${categoria.cat}\"?")
            .setPositiveButton("Sim") { _, _ ->
                viewModel.deleteCategoria(categoria)
                Toast.makeText(requireContext(), "Categoria excluída.", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("Não", null)
            .show()
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}