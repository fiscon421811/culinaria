package com.example.culinaria.planner

import android.content.Context
import com.google.gson.Gson
import com.google.gson.JsonParser
import com.google.gson.reflect.TypeToken

data class PlannedMeal(
    val title: String,
    val recipe: String,
    val link: String? = null,
)

data class MealPlannerState(
    val meals: Map<String, List<PlannedMeal>> = emptyMap(),
)

class MealPlannerStore(context: Context) {
    private val preferences = context.getSharedPreferences(PREFERENCES_NAME, Context.MODE_PRIVATE)
    private val gson = Gson()

    fun load(): MealPlannerState {
        val json = preferences.getString(KEY_STATE, null) ?: return MealPlannerState()
        return runCatching {
            val mealsObject = JsonParser().parse(json).asJsonObject.getAsJsonObject("meals")
                ?: return@runCatching MealPlannerState()
            val meals = mutableMapOf<String, List<PlannedMeal>>()

            for (entry in mealsObject.entrySet()) {
                val plannedMeals: List<PlannedMeal> = when {
                    entry.value.isJsonArray -> gson.fromJson(
                        entry.value,
                        object : TypeToken<List<PlannedMeal>>() {}.type,
                    )
                    entry.value.isJsonObject -> listOf(gson.fromJson(entry.value, PlannedMeal::class.java))
                    else -> emptyList()
                }
                meals[entry.key] = plannedMeals
            }
            MealPlannerState(meals)
        }.getOrDefault(MealPlannerState())
    }
    fun save(state: MealPlannerState) {
        // O cardápio deve sobreviver mesmo se o processo for encerrado logo após a ação.
        preferences.edit().putString(KEY_STATE, gson.toJson(state)).commit()
    }

    companion object {
        private const val PREFERENCES_NAME = "meal_planner"
        private const val KEY_STATE = "state"
    }
}