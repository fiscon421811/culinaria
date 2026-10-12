package com.example.culinaria.adapter

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.DiffUtil
import androidx.recyclerview.widget.ListAdapter
import androidx.recyclerview.widget.RecyclerView
import com.example.culinaria.databinding.ItemReceitaBinding
import com.example.culinaria.model.Receita

class ReceitaAdapter(
    private val onItemClick: (Receita) -> Unit
) : ListAdapter<Receita, ReceitaAdapter.ReceitaViewHolder>(DIFF_CALLBACK) {

    inner class ReceitaViewHolder(private val binding: ItemReceitaBinding) :
        RecyclerView.ViewHolder(binding.root) {

        fun bind(receita: Receita) {
            // Usa Cod se > 0, senão usa ID
            val codigoExibido = if (receita.cod > 0) receita.cod else receita.id
            binding.tvCod.text = codigoExibido.toString().padStart(3, '0')
            binding.tvTitulo.text = receita.titulo
            binding.root.setOnClickListener { onItemClick(receita) }
        }
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ReceitaViewHolder {
        val binding = ItemReceitaBinding.inflate(
            LayoutInflater.from(parent.context), parent, false
        )
        return ReceitaViewHolder(binding)
    }

    override fun onBindViewHolder(holder: ReceitaViewHolder, position: Int) {
        holder.bind(getItem(position))
    }

    companion object {
        val DIFF_CALLBACK = object : DiffUtil.ItemCallback<Receita>() {
            override fun areItemsTheSame(oldItem: Receita, newItem: Receita) =
                oldItem.id == newItem.id

            override fun areContentsTheSame(oldItem: Receita, newItem: Receita) =
                oldItem == newItem
        }
    }
}