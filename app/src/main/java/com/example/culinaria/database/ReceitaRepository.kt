package com.example.culinaria.database

import android.content.Context
import android.util.Log
import com.google.gson.Gson
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class ReceitaRepository(private val context: Context) {

    private val apiService = TursoClient.apiService
    private val gson = Gson()

    interface ReceitaCallback {
        fun onSuccess(result: List<com.example.culinaria.database.Receita>)
        fun onError(error: String)
    }

    interface CategoriaCallback {
        fun onSuccess(result: List<com.example.culinaria.database.Categoria>)
        fun onError(error: String)
    }

    interface SimpleCallback {
        fun onSuccess()
        fun onError(error: String)
    }

    // Buscar todas as categorias
    fun buscarCategorias(callback: CategoriaCallback) {
        val sql = "SELECT CodCat, Cat FROM categorias ORDER BY Cat"

        val request = TursoQueryRequest(
            listOf(TursoRequest(stmt = TursoStatement(sql, null)))
        )

        apiService.executeQuery(request).enqueue(object : Callback<TursoQueryResponse> {
            override fun onResponse(call: Call<TursoQueryResponse>, response: Response<TursoQueryResponse>) {
                if (response.isSuccessful && response.body() != null) {
                    val categorias = parseCategoriasFromResponse(response.body()!!)
                    callback.onSuccess(categorias)
                } else {
                    callback.onError("Erro: ${response.code()}")
                }
            }

            override fun onFailure(call: Call<TursoQueryResponse>, t: Throwable) {
                callback.onError("Falha: ${t.message}")
            }
        })
    }

    // Buscar todas as receitas com nome da categoria
    fun buscarTodasReceitas(callback: ReceitaCallback) {
        val sql = """
            SELECT r.ID, r.Cod, r.CodCat, r.Titulo, r.Receita, r.Link, c.Cat as nomeCategoria
            FROM receitas r
            LEFT JOIN categorias c ON r.CodCat = c.CodCat
            ORDER BY r.ID DESC
        """.trimIndent()

        val request = TursoQueryRequest(
            listOf(TursoRequest(stmt = TursoStatement(sql, null)))
        )

        apiService.executeQuery(request).enqueue(object : Callback<TursoQueryResponse> {
            override fun onResponse(call: Call<TursoQueryResponse>, response: Response<TursoQueryResponse>) {
                if (response.isSuccessful && response.body() != null) {
                    val receitas = parseReceitasFromResponse(response.body()!!)
                    callback.onSuccess(receitas)
                } else {
                    callback.onError("Erro: ${response.code()}")
                }
            }

            override fun onFailure(call: Call<TursoQueryResponse>, t: Throwable) {
                callback.onError("Falha: ${t.message}")
            }
        })
    }

    // Buscar receita por ID
    fun buscarReceitaPorId(id: Int, callback: (com.example.culinaria.database.Receita?) -> Unit) {
        val sql = """
            SELECT r.ID, r.Cod, r.CodCat, r.Titulo, r.Receita, r.Link, c.Cat as nomeCategoria
            FROM receitas r
            LEFT JOIN categorias c ON r.CodCat = c.CodCat
            WHERE r.ID = ?
        """.trimIndent()

        val args = listOf(TursoArg("text", id.toString()))

        val request = TursoQueryRequest(
            listOf(TursoRequest(stmt = TursoStatement(sql, args)))
        )

        apiService.executeQuery(request).enqueue(object : Callback<TursoQueryResponse> {
            override fun onResponse(call: Call<TursoQueryResponse>, response: Response<TursoQueryResponse>) {
                if (response.isSuccessful && response.body() != null) {
                    val receitas = parseReceitasFromResponse(response.body()!!)
                    callback(receitas.firstOrNull())
                } else {
                    callback(null)
                }
            }

            override fun onFailure(call: Call<TursoQueryResponse>, t: Throwable) {
                callback(null)
            }
        })
    }

    fun buscarReceitaPorLink(link: String, callback: (com.example.culinaria.database.Receita?) -> Unit) {
        val sql = """
            SELECT r.ID, r.Cod, r.CodCat, r.Titulo, r.Receita, r.Link, c.Cat as nomeCategoria
            FROM receitas r
            LEFT JOIN categorias c ON r.CodCat = c.CodCat
            WHERE r.Link = ?
            LIMIT 1
        """.trimIndent()

        val args = listOf(TursoArg("text", link))
        val request = TursoQueryRequest(listOf(TursoRequest(stmt = TursoStatement(sql, args))))

        apiService.executeQuery(request).enqueue(object : Callback<TursoQueryResponse> {
            override fun onResponse(call: Call<TursoQueryResponse>, response: Response<TursoQueryResponse>) {
                callback(if (response.isSuccessful && response.body() != null) {
                    parseReceitasFromResponse(response.body()!!).firstOrNull()
                } else null)
            }

            override fun onFailure(call: Call<TursoQueryResponse>, t: Throwable) = callback(null)
        })
    }
    // Buscar receitas por categoria
    fun buscarPorCategoria(codCat: Int, callback: ReceitaCallback) {
        val sql = """
            SELECT r.ID, r.Cod, r.CodCat, r.Titulo, r.Receita, r.Link, c.Cat as nomeCategoria
            FROM receitas r
            LEFT JOIN categorias c ON r.CodCat = c.CodCat
            WHERE r.CodCat = ?
            ORDER BY r.Titulo
        """.trimIndent()

        val args = listOf(TursoArg("text", codCat.toString()))

        val request = TursoQueryRequest(
            listOf(TursoRequest(stmt = TursoStatement(sql, args)))
        )

        apiService.executeQuery(request).enqueue(object : Callback<TursoQueryResponse> {
            override fun onResponse(call: Call<TursoQueryResponse>, response: Response<TursoQueryResponse>) {
                if (response.isSuccessful && response.body() != null) {
                    val receitas = parseReceitasFromResponse(response.body()!!)
                    callback.onSuccess(receitas)
                } else {
                    callback.onError("Erro: ${response.code()}")
                }
            }

            override fun onFailure(call: Call<TursoQueryResponse>, t: Throwable) {
                callback.onError("Falha: ${t.message}")
            }
        })
    }

    // Buscar receitas por termo
    fun buscarPorTermo(termo: String, callback: ReceitaCallback) {
        val sql = """
            SELECT r.ID, r.Cod, r.CodCat, r.Titulo, r.Receita, r.Link, c.Cat as nomeCategoria
            FROM receitas r
            LEFT JOIN categorias c ON r.CodCat = c.CodCat
            WHERE r.Titulo LIKE ? OR r.Receita LIKE ?
            ORDER BY r.Titulo
        """.trimIndent()

        val args = listOf(
            TursoArg("text", "%$termo%"),
            TursoArg("text", "%$termo%")
        )

        val request = TursoQueryRequest(
            listOf(TursoRequest(stmt = TursoStatement(sql, args)))
        )

        apiService.executeQuery(request).enqueue(object : Callback<TursoQueryResponse> {
            override fun onResponse(call: Call<TursoQueryResponse>, response: Response<TursoQueryResponse>) {
                if (response.isSuccessful && response.body() != null) {
                    val receitas = parseReceitasFromResponse(response.body()!!)
                    callback.onSuccess(receitas)
                } else {
                    callback.onError("Erro: ${response.code()}")
                }
            }

            override fun onFailure(call: Call<TursoQueryResponse>, t: Throwable) {
                callback.onError("Falha: ${t.message}")
            }
        })
    }

    // Inserir nova receita
    fun inserirReceita(receita: com.example.culinaria.database.Receita, callback: SimpleCallback) {
        val sql = """
            INSERT INTO receitas (Cod, CodCat, Titulo, Receita, Link)
            VALUES (?, ?, ?, ?, ?)
        """.trimIndent()

        val args = listOf(
            TursoArg("text", receita.Cod.toString()),
            TursoArg("text", receita.CodCat.toString()),
            TursoArg("text", receita.Titulo),
            TursoArg("text", receita.Receita),
            TursoArg("text", receita.Link ?: "")
        )

        val request = TursoQueryRequest(
            listOf(TursoRequest(stmt = TursoStatement(sql, args)))
        )

        apiService.executeQuery(request).enqueue(object : Callback<TursoQueryResponse> {
            override fun onResponse(call: Call<TursoQueryResponse>, response: Response<TursoQueryResponse>) {
                if (response.isSuccessful) {
                    callback.onSuccess()
                } else {
                    callback.onError("Erro ao inserir")
                }
            }

            override fun onFailure(call: Call<TursoQueryResponse>, t: Throwable) {
                callback.onError("Falha: ${t.message}")
            }
        })
    }

    // Atualizar receita
    fun atualizarReceita(id: Int, receita: com.example.culinaria.database.Receita, callback: SimpleCallback) {
        val sql = """
            UPDATE receitas 
            SET CodCat = ?, Titulo = ?, Receita = ?, Link = ?
            WHERE ID = ?
        """.trimIndent()

        val args = listOf(
            TursoArg("text", receita.CodCat.toString()),
            TursoArg("text", receita.Titulo),
            TursoArg("text", receita.Receita),
            TursoArg("text", receita.Link ?: ""),
            TursoArg("text", id.toString())
        )

        val request = TursoQueryRequest(
            listOf(TursoRequest(stmt = TursoStatement(sql, args)))
        )

        apiService.executeQuery(request).enqueue(object : Callback<TursoQueryResponse> {
            override fun onResponse(call: Call<TursoQueryResponse>, response: Response<TursoQueryResponse>) {
                if (response.isSuccessful) {
                    callback.onSuccess()
                } else {
                    callback.onError("Erro ao atualizar")
                }
            }

            override fun onFailure(call: Call<TursoQueryResponse>, t: Throwable) {
                callback.onError("Falha: ${t.message}")
            }
        })
    }

    // Deletar receita
    fun deletarReceita(id: Int, callback: SimpleCallback) {
        val sql = "DELETE FROM receitas WHERE ID = ?"
        val args = listOf(TursoArg("text", id.toString()))

        val request = TursoQueryRequest(
            listOf(TursoRequest(stmt = TursoStatement(sql, args)))
        )

        apiService.executeQuery(request).enqueue(object : Callback<TursoQueryResponse> {
            override fun onResponse(call: Call<TursoQueryResponse>, response: Response<TursoQueryResponse>) {
                if (response.isSuccessful) {
                    callback.onSuccess()
                } else {
                    callback.onError("Erro ao deletar")
                }
            }

            override fun onFailure(call: Call<TursoQueryResponse>, t: Throwable) {
                callback.onError("Falha: ${t.message}")
            }
        })
    }

    private fun parseCategoriasFromResponse(response: TursoQueryResponse): List<com.example.culinaria.database.Categoria> {
        val categorias = mutableListOf<com.example.culinaria.database.Categoria>()

        try {
            response.results.forEach { result ->
                val rows = result.response.result.rows
                val cols = result.response.result.cols

                rows.forEach { row ->
                    val rowMap = mutableMapOf<String, Any?>()
                    cols.forEachIndexed { index, col ->
                        if (index < row.size) {
                            rowMap[col.name] = row[index].value
                        }
                    }

                    val codCat = when (val v = rowMap["CodCat"]) {
                        is Number -> v.toInt()
                        is String -> v.toIntOrNull() ?: 0
                        else -> 0
                    }

                    val categoria = com.example.culinaria.database.Categoria(
                        CodCat = codCat,
                        Cat = rowMap["Cat"]?.toString() ?: ""
                    )
                    categorias.add(categoria)
                }
            }
        } catch (e: Exception) {
            Log.e("TursoDB", "Erro ao parsear categorias", e)
        }

        return categorias
    }

    private fun parseReceitasFromResponse(response: TursoQueryResponse): List<com.example.culinaria.database.Receita> {
        val receitas = mutableListOf<com.example.culinaria.database.Receita>()

        try {
            response.results.forEach { result ->
                val rows = result.response.result.rows
                val cols = result.response.result.cols

                rows.forEach { row ->
                    val rowMap = mutableMapOf<String, Any?>()
                    cols.forEachIndexed { index, col ->
                        if (index < row.size) {
                            rowMap[col.name] = row[index].value
                        }
                    }

                    val id = when (val v = rowMap["ID"]) {
                        is Number -> v.toInt()
                        is String -> v.toIntOrNull() ?: 0
                        else -> 0
                    }

                    val cod = when (val v = rowMap["Cod"]) {
                        is Number -> v.toInt()
                        is String -> v.toIntOrNull() ?: 0
                        else -> 0
                    }

                    val codCat = when (val v = rowMap["CodCat"]) {
                        is Number -> v.toInt()
                        is String -> v.toIntOrNull() ?: 0
                        else -> 0
                    }

                    val receita = com.example.culinaria.database.Receita(
                        ID = id,
                        Cod = cod,
                        CodCat = codCat,
                        Titulo = rowMap["Titulo"]?.toString() ?: "",
                        Receita = rowMap["Receita"]?.toString() ?: "",
                        Link = rowMap["Link"]?.toString(),
                        nomeCategoria = rowMap["nomeCategoria"]?.toString() ?: ""
                    )
                    receitas.add(receita)
                }
            }
        } catch (e: Exception) {
            Log.e("TursoDB", "Erro ao parsear receitas", e)
        }

        return receitas
    }
}
