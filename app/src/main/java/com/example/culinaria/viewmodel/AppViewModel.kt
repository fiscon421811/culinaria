package com.example.culinaria.viewmodel

import android.app.Application
import androidx.lifecycle.*
import com.example.culinaria.model.Categoria
import com.example.culinaria.model.Receita
import com.example.culinaria.repository.AppRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class AppViewModel(application: Application) : AndroidViewModel(application) {

    private val repository = AppRepository(application)

    private val _homeReceitas = MutableLiveData<List<Receita>>(emptyList())
    val homeReceitas: LiveData<List<Receita>> = _homeReceitas

    private val _editarReceitas = MutableLiveData<List<Receita>>(emptyList())
    val editarReceitas: LiveData<List<Receita>> = _editarReceitas

    private val _categorias = MutableLiveData<List<Categoria>>(emptyList())
    val allCategorias: LiveData<List<Categoria>> = _categorias

    private val _erro = MutableLiveData<String?>()
    val erro: LiveData<String?> = _erro

    private val _loading = MutableLiveData(false)
    val loading: LiveData<Boolean> = _loading

    init {
        carregarTudo()
    }

    fun carregarTudo() {
        io {
            _homeReceitas.postValue(repository.getAllReceitas())
            _categorias.postValue(repository.getAllCategorias())
        }
    }

    fun searchHomeReceitas(titulo: String, ingrediente: String) = io {
        _homeReceitas.postValue(repository.search(titulo, ingrediente))
    }

    fun filterByCategoria(codCat: Int) = io {
        _homeReceitas.postValue(repository.getByCategoria(codCat))
    }

    fun showAllReceitas() = io {
        _homeReceitas.postValue(repository.getAllReceitas())
    }

    fun searchEditarReceitas(titulo: String, ingrediente: String) = io {
        _editarReceitas.postValue(repository.search(titulo, ingrediente))
    }

    suspend fun getByCod(cod: Int): Receita? = withContext(Dispatchers.IO) {
        repository.getByCod(cod)
    }

    suspend fun getByLink(link: String): Receita? = withContext(Dispatchers.IO) {
        repository.getByLink(link)
    }
    suspend fun getNextCod(): Int = withContext(Dispatchers.IO) {
        repository.getMaxCod() + 1
    }

    fun insertReceita(receita: Receita) = io {
        repository.insertReceita(receita)
        _homeReceitas.postValue(repository.getAllReceitas())
        _editarReceitas.postValue(repository.getAllReceitas())
    }

    fun updateReceita(receita: Receita) = io {
        repository.updateReceita(receita)
        _homeReceitas.postValue(repository.getAllReceitas())
        _editarReceitas.postValue(repository.getAllReceitas())
    }

    fun deleteReceita(cod: Int) = io {
        repository.deleteReceita(cod)
        _homeReceitas.postValue(repository.getAllReceitas())
        _editarReceitas.postValue(repository.getAllReceitas())
    }


    /** Reconsulta a tabela categorias para evitar usar uma lista em memória desatualizada. */
    suspend fun refreshCategorias(): List<Categoria> = withContext(Dispatchers.IO) {
        repository.getAllCategorias(forceRefresh = true).also { _categorias.postValue(it) }
    }
    suspend fun getNextCodCat(): Int = withContext(Dispatchers.IO) {
        repository.getMaxCodCat() + 1
    }

    fun insertCategoria(categoria: Categoria) = io {
        repository.insertCategoria(categoria)
        _categorias.postValue(repository.getAllCategorias())
    }

    fun updateCategoria(categoria: Categoria) = io {
        repository.updateCategoria(categoria)
        _categorias.postValue(repository.getAllCategorias())
    }

    fun deleteCategoria(categoria: Categoria) = io {
        repository.deleteCategoria(categoria)
        _categorias.postValue(repository.getAllCategorias())
    }

    private fun io(block: suspend () -> Unit) = viewModelScope.launch(Dispatchers.IO) {
        try {
            _loading.postValue(true)
            block()
        } catch (e: Exception) {
            _erro.postValue("Erro: ${e.message}")
        } finally {
            _loading.postValue(false)
        }
    }
}
