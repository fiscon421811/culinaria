package com.example.culinaria.repository

import android.content.Context
import com.example.culinaria.database.Receita
import com.example.culinaria.database.ReceitaRepository
import com.example.culinaria.model.Categoria
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException
import kotlin.coroutines.suspendCoroutine

class AppRepository(private val context: Context) {

    private val tursoRepo = ReceitaRepository(context)
    private var cachedCategorias: List<Categoria>? = null
    private var cachedReceitas: List<com.example.culinaria.model.Receita>? = null

    // â”€â”€ Categorias â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    suspend fun getAllCategorias(forceRefresh: Boolean = false): List<Categoria> = withContext(Dispatchers.IO) {
        if (!forceRefresh && cachedCategorias != null) return@withContext cachedCategorias!!

        return@withContext suspendCoroutine { continuation ->
            tursoRepo.buscarCategorias(object : ReceitaRepository.CategoriaCallback {
                override fun onSuccess(result: List<com.example.culinaria.database.Categoria>) {
                    val categorias = result.map { dbCat ->
                        Categoria(
                            id = dbCat.CodCat,
                            codCat = dbCat.CodCat,
                            cat = dbCat.Cat
                        )
                    }
                    cachedCategorias = categorias
                    continuation.resume(categorias)
                }

                override fun onError(error: String) {
                    continuation.resume(emptyList())
                }
            })
        }
    }

    suspend fun getMaxCodCat(): Int = withContext(Dispatchers.IO) {
        val categorias = getAllCategorias()
        categorias.maxOfOrNull { it.codCat } ?: 0
    }

    suspend fun insertCategoria(categoria: Categoria) = withContext(Dispatchers.IO) {
        val currentList = cachedCategorias?.toMutableList() ?: mutableListOf()
        currentList.add(categoria)
        cachedCategorias = currentList
    }

    suspend fun updateCategoria(categoria: Categoria) = withContext(Dispatchers.IO) {
        cachedCategorias = cachedCategorias?.map {
            if (it.codCat == categoria.codCat) it.copy(cat = categoria.cat) else it
        }
    }

    suspend fun deleteCategoria(categoria: Categoria) = withContext(Dispatchers.IO) {
        cachedCategorias = cachedCategorias?.filter { it.codCat != categoria.codCat }
    }

    // â”€â”€ Receitas â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

    suspend fun getAllReceitas(): List<com.example.culinaria.model.Receita> = withContext(Dispatchers.IO) {
        if (cachedReceitas != null) return@withContext cachedReceitas!!

        return@withContext suspendCoroutine { continuation ->
            tursoRepo.buscarTodasReceitas(object : ReceitaRepository.ReceitaCallback {
                override fun onSuccess(result: List<Receita>) {
                    val receitas = result.map { dbReceita ->
                        com.example.culinaria.model.Receita(
                            id = dbReceita.ID,
                            cod = dbReceita.Cod,
                            codCat = dbReceita.CodCat,
                            titulo = dbReceita.Titulo,
                            receita = dbReceita.Receita,
                            link = dbReceita.Link
                        )
                    }
                    cachedReceitas = receitas
                    continuation.resume(receitas)
                }

                override fun onError(error: String) {
                    continuation.resume(emptyList())
                }
            })
        }
    }

    suspend fun search(titulo: String, ingrediente: String): List<com.example.culinaria.model.Receita> = withContext(Dispatchers.IO) {
        val normalizedTitle = normalizeForSearch(titulo)
        val normalizedIngredient = normalizeForSearch(ingrediente)
        if (normalizedTitle.isBlank() && normalizedIngredient.isBlank()) return@withContext getAllReceitas()

        getAllReceitas().filter { receita ->
            (normalizedTitle.isBlank() || normalizeForSearch(receita.titulo).contains(normalizedTitle)) &&
                (normalizedIngredient.isBlank() || normalizeForSearch(receita.receita).contains(normalizedIngredient))
        }
    }

    private fun normalizeForSearch(value: String): String =
        java.text.Normalizer.normalize(value, java.text.Normalizer.Form.NFD)
            .replace(Regex("\\p{Mn}+"), "")
            .lowercase(java.util.Locale.ROOT)

    suspend fun getByCategoria(codCat: Int): List<com.example.culinaria.model.Receita> = withContext(Dispatchers.IO) {
        suspendCoroutine { continuation ->
            tursoRepo.buscarPorCategoria(codCat, object : ReceitaRepository.ReceitaCallback {
                override fun onSuccess(result: List<Receita>) {
                    val receitas = result.map { dbReceita ->
                        com.example.culinaria.model.Receita(
                            id = dbReceita.ID,
                            cod = dbReceita.Cod,
                            codCat = dbReceita.CodCat,
                            titulo = dbReceita.Titulo,
                            receita = dbReceita.Receita,
                            link = dbReceita.Link
                        )
                    }
                    continuation.resume(receitas)
                }

                override fun onError(error: String) {
                    continuation.resume(emptyList())
                }
            })
        }
    }

    suspend fun getByCod(cod: Int): com.example.culinaria.model.Receita? = withContext(Dispatchers.IO) {
        val todas = getAllReceitas()
        todas.firstOrNull { it.cod == cod }
    }

    suspend fun getByLink(link: String): com.example.culinaria.model.Receita? = withContext(Dispatchers.IO) {
        suspendCoroutine { continuation ->
            tursoRepo.buscarReceitaPorLink(link) { dbReceita ->
                continuation.resume(dbReceita?.let {
                    com.example.culinaria.model.Receita(
                        id = it.ID, cod = it.Cod, codCat = it.CodCat,
                        titulo = it.Titulo, receita = it.Receita, link = it.Link,
                    )
                })
            }
        }
    }
    suspend fun getMaxCod(): Int = withContext(Dispatchers.IO) {
        val receitas = getAllReceitas()
        receitas.maxOfOrNull { it.cod } ?: 0
    }

    suspend fun insertReceita(receita: com.example.culinaria.model.Receita) = withContext(Dispatchers.IO) {
        suspendCoroutine<Unit> { continuation ->
            val dbReceita = Receita(
                Cod = receita.cod,
                CodCat = receita.codCat,
                Titulo = receita.titulo,
                Receita = receita.receita,
                Link = receita.link
            )

            tursoRepo.inserirReceita(dbReceita, object : ReceitaRepository.SimpleCallback {
                override fun onSuccess() {
                    cachedReceitas = null
                    continuation.resume(Unit)
                }

                override fun onError(error: String) {
                    continuation.resume(Unit)
                }
            })
        }
    }

    suspend fun updateReceita(receita: com.example.culinaria.model.Receita) = withContext(Dispatchers.IO) {
        suspendCoroutine<Unit> { continuation ->
            tursoRepo.buscarReceitaPorId(receita.id) { dbReceita ->
                if (dbReceita != null) {
                    val receitaAtualizada = dbReceita.copy(
                        Titulo = receita.titulo,
                        Receita = receita.receita,
                        Link = receita.link
                    )
                    tursoRepo.atualizarReceita(receita.id, receitaAtualizada, object : ReceitaRepository.SimpleCallback {
                        override fun onSuccess() {
                            cachedReceitas = null
                            continuation.resume(Unit)
                        }

                        override fun onError(error: String) {
                            continuation.resume(Unit)
                        }
                    })
                } else {
                    continuation.resume(Unit)
                }
            }
        }
    }

    suspend fun deleteReceita(cod: Int) = withContext(Dispatchers.IO) {
        val receita = getByCod(cod)
        receita?.let {
            suspendCoroutine<Unit> { continuation ->
                tursoRepo.deletarReceita(it.id, object : ReceitaRepository.SimpleCallback {
                    override fun onSuccess() {
                        cachedReceitas = null
                        continuation.resume(Unit)
                    }

                    override fun onError(error: String) {
                        continuation.resume(Unit)
                    }
                })
            }
        }
    }
}
