package com.example.culinaria

import android.os.Bundle
import android.widget.*
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.example.culinaria.database.*
import com.google.android.material.button.MaterialButton
import com.google.android.material.textfield.TextInputEditText

class EditarReceitaActivity : AppCompatActivity() {

    private lateinit var repository: ReceitaRepository
    private var receitaId: Int = 0
    private var isEditing = false
    private var categoriasList = listOf<Categoria>()

    private lateinit var inputTitulo: TextInputEditText
    private lateinit var inputReceita: TextInputEditText
    private lateinit var inputLink: TextInputEditText
    private lateinit var spinnerCategoria: Spinner
    private lateinit var buttonSalvar: MaterialButton
    private lateinit var buttonDelete: MaterialButton

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_editar_receita)

        repository = ReceitaRepository(this)
        receitaId = intent.getIntExtra("receita_id", 0)
        isEditing = receitaId != 0

        setupViews()
        carregarCategorias()

        if (isEditing) {
            supportActionBar?.title = "Editar Receita"
            carregarReceita()
        } else {
            supportActionBar?.title = "Nova Receita"
            buttonDelete.visibility = android.view.View.GONE
        }

        buttonSalvar.setOnClickListener { salvarReceita() }
        buttonDelete.setOnClickListener { confirmarDelete() }
    }

    private fun setupViews() {
        inputTitulo = findViewById(R.id.inputTitulo)
        inputReceita = findViewById(R.id.inputReceita)
        inputLink = findViewById(R.id.inputLink)
        spinnerCategoria = findViewById(R.id.spinnerCategoria)
        buttonSalvar = findViewById(R.id.buttonSalvar)
        buttonDelete = findViewById(R.id.buttonDelete)
    }

    private fun carregarCategorias() {
        repository.buscarCategorias(object : ReceitaRepository.CategoriaCallback {
            override fun onSuccess(result: List<Categoria>) {
                categoriasList = result
                configurarSpinnerCategorias()
            }

            override fun onError(error: String) {
                Toast.makeText(this@EditarReceitaActivity, "Erro ao carregar categorias: $error", Toast.LENGTH_SHORT).show()
            }
        })
    }

    private fun configurarSpinnerCategorias() {
        val categoriasNomes = categoriasList.map { it.Cat }
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, categoriasNomes)
        adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
        spinnerCategoria.adapter = adapter
    }

    private fun carregarReceita() {
        repository.buscarReceitaPorId(receitaId) { receita ->
            receita?.let {
                inputTitulo.setText(it.Titulo)
                inputReceita.setText(it.Receita)
                inputLink.setText(it.Link ?: "")

                val categoriaIndex = categoriasList.indexOfFirst { cat -> cat.CodCat == it.CodCat }
                if (categoriaIndex >= 0) {
                    spinnerCategoria.setSelection(categoriaIndex)
                }
            }
        }
    }

    private fun salvarReceita() {
        val titulo = inputTitulo.text.toString().trim()
        val receitaText = inputReceita.text.toString().trim()
        val link = inputLink.text.toString().trim()
        val categoriaPos = spinnerCategoria.selectedItemPosition

        if (titulo.isEmpty()) {
            inputTitulo.error = "Digite o título da receita"
            return
        }

        if (receitaText.isEmpty()) {
            inputReceita.error = "Digite a receita"
            return
        }

        if (categoriaPos < 0 || categoriaPos >= categoriasList.size) {
            Toast.makeText(this, "Selecione uma categoria", Toast.LENGTH_SHORT).show()
            return
        }

        val codCat = categoriasList[categoriaPos].CodCat

        val receita = Receita(
            CodCat = codCat,
            Titulo = titulo,
            Receita = receitaText,
            Link = link.ifEmpty { null }
        )

        if (isEditing) {
            repository.atualizarReceita(receitaId, receita, object : ReceitaRepository.SimpleCallback {
                override fun onSuccess() {
                    Toast.makeText(this@EditarReceitaActivity, "Receita atualizada!", Toast.LENGTH_SHORT).show()
                    finish()
                }

                override fun onError(error: String) {
                    Toast.makeText(this@EditarReceitaActivity, error, Toast.LENGTH_SHORT).show()
                }
            })
        } else {
            repository.inserirReceita(receita, object : ReceitaRepository.SimpleCallback {
                override fun onSuccess() {
                    Toast.makeText(this@EditarReceitaActivity, "Receita salva!", Toast.LENGTH_SHORT).show()
                    finish()
                }

                override fun onError(error: String) {
                    Toast.makeText(this@EditarReceitaActivity, error, Toast.LENGTH_SHORT).show()
                }
            })
        }
    }

    private fun confirmarDelete() {
        AlertDialog.Builder(this)
            .setTitle("Excluir Receita")
            .setMessage("Tem certeza que deseja excluir esta receita?")
            .setPositiveButton("Excluir") { _, _ ->
                repository.deletarReceita(receitaId, object : ReceitaRepository.SimpleCallback {
                    override fun onSuccess() {
                        Toast.makeText(this@EditarReceitaActivity, "Receita excluída!", Toast.LENGTH_SHORT).show()
                        finish()
                    }

                    override fun onError(error: String) {
                        Toast.makeText(this@EditarReceitaActivity, error, Toast.LENGTH_SHORT).show()
                    }
                })
            }
            .setNegativeButton("Cancelar", null)
            .show()
    }
}