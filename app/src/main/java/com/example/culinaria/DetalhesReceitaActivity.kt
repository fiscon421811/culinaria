package com.example.culinaria

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.example.culinaria.database.ReceitaRepository

class DetalhesReceitaActivity : AppCompatActivity() {

    private lateinit var repository: ReceitaRepository
    private var receitaId: Int = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_detalhes_receita)

        repository = ReceitaRepository(this)
        receitaId = intent.getIntExtra("receita_id", 0)

        val buttonEdit: Button = findViewById(R.id.buttonEdit)
        val buttonBack: Button = findViewById(R.id.buttonBack)

        buttonEdit.setOnClickListener {
            val intent = Intent(this, EditarReceitaActivity::class.java)
            intent.putExtra("receita_id", receitaId)
            startActivity(intent)
        }

        buttonBack.setOnClickListener {
            finish()
        }

        carregarDetalhes()
    }

    private fun carregarDetalhes() {
        repository.buscarReceitaPorId(receitaId) { receita ->
            receita?.let {
                findViewById<TextView>(R.id.textTitulo).text = it.Titulo
                findViewById<TextView>(R.id.textCategoria).text = "📂 ${it.nomeCategoria}"
                findViewById<TextView>(R.id.textCod).text = "🔢 Código: ${it.Cod}"

                findViewById<TextView>(R.id.textReceita).text = it.Receita

                val textLink = findViewById<TextView>(R.id.textLink)
                if (it.Link.isNullOrEmpty()) {
                    textLink.visibility = android.view.View.GONE
                } else {
                    textLink.text = "🔗 Link: ${it.Link}"
                    textLink.visibility = android.view.View.VISIBLE
                }
            }
        }
    }
}