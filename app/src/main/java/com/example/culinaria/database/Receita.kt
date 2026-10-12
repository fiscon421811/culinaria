package com.example.culinaria.database

data class Receita(
    val ID: Int = 0,
    val Cod: Int = 0,
    val CodCat: Int = 0,
    val Titulo: String = "",
    val Receita: String = "",
    val Link: String? = null,
    val nomeCategoria: String = "" // Para exibição
)

data class Categoria(
    val CodCat: Int = 0,
    val Cat: String = ""
)