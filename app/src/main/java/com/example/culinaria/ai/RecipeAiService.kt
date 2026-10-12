package com.example.culinaria.ai

import com.example.culinaria.BuildConfig
import okhttp3.OkHttpClient
import java.util.concurrent.TimeUnit
import retrofit2.Call
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST

data class RecipeAiRequest(val url: String, val context: String? = null)
data class SeasonalRecipeRequest(val title: String, val season: String, val meal: String, val day: String, val videoUrl: String? = null)
data class VideoRecipeSearchRequest(val query: String)
data class VideoRecipeResult(val title: String, val url: String)
data class VideoRecipeSearchResponse(val results: List<VideoRecipeResult> = emptyList())
data class Ingredient(val nome: String, val quantidade: String)
data class RecipeAiResponse(
    val titulo: String,
    val ingredientes: List<Ingredient>,
    val modoPreparo: String?,
    val videoUrl: String? = null,
)
data class RecipeAiError(val error: String?)

interface RecipeAiService {
    @POST("extract-recipe")
    fun extractRecipe(@Body request: RecipeAiRequest): Call<RecipeAiResponse>

    @POST("generate-seasonal-recipe")
    fun generateSeasonalRecipe(@Body request: SeasonalRecipeRequest): Call<RecipeAiResponse>

    @POST("search-video-recipes")
    fun searchVideoRecipes(@Body request: VideoRecipeSearchRequest): Call<VideoRecipeSearchResponse>
}

object RecipeAiClient {
    val service: RecipeAiService by lazy {
        val httpClient = OkHttpClient.Builder()
            .connectTimeout(20, TimeUnit.SECONDS)
            .readTimeout(90, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.SECONDS)
            .callTimeout(100, TimeUnit.SECONDS)
            .build()

        Retrofit.Builder()
            .baseUrl(BuildConfig.MEAL_AI_BASE_URL)
            .client(httpClient)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(RecipeAiService::class.java)
    }
}
