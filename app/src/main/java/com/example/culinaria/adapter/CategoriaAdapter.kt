package com.example.culinaria.adapter

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.culinaria.databinding.ItemCategoriaBinding
import com.example.culinaria.model.Categoria

class CategoriaAdapter(
    private val onDelete: (Categoria) -> Unit,
    private val onUpdate: (Categoria) -> Unit
) : ListAdapter<Categoria, CategoriaAdapter.CategoriaViewHolder>(DIFF_CALLBACK) {

    inner class CategoriaViewHolder(private val binding: ItemCategoriaBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(categoria: Categoria) {
            binding.tvCodCat.text = categoria.codCat.toString()
            binding.etCat.setText(categoria.cat)

            binding.btnDelete.setOnClickListener { onDelete(categoria) }

            binding.btnSave.setOnClickListener {
                val novoNome = binding.etCat.text.toString().trim()
                if (novoNome.isNotEmpty()) {
                    onUpdate(categoria.copy(cat = novoNome))
                }
            }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): CategoriaViewHolder {
        val binding = ItemCategoriaBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return CategoriaViewHolder(binding)
    }

    override fun onBindViewHolder(holder: CategoriaViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    companion object {
        val DIFF_CALLBACK = object : DiffUtil.ItemCallback<Categoria>() {
            override fun areItemsTheSame(oldItem: Categoria, newItem: Categoria) =
                oldItem.id == newItem.id

            override fun areContentsTheSame(oldItem: Categoria, newItem: Categoria) =
                oldItem == newItem
        }
    }
}