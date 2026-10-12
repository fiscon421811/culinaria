package com.example.culinaria.model

data class Receita(
    val id: Int = 0,
    val cod: Int = 0,
    val codCat: Int = 0,
    val titulo: String = "",
    val receita: String = "",
    val link: String? = null
)