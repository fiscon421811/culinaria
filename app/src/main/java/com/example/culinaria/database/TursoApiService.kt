package com.example.culinaria.database

import retrofit2.Call
import retrofit2.http.*

interface TursoApiService {
    @POST("db")
    @Headers("Content-Type: application/json")
    fun executeQuery(
        @Body request: TursoQueryRequest
    ): Call<TursoQueryResponse>
}
