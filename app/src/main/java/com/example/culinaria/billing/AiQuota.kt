package com.example.culinaria.billing

import android.content.Context
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Cota diária gratuita das funções de IA (importar receita, gerar receita do cardápio).
 * Assinantes Premium não têm limite. A contagem zera a cada dia.
 */
object AiQuota {
    const val FREE_DAILY_LIMIT = 3

    private const val PREFS = "ai_quota"
    private const val KEY_DAY = "day"
    private const val KEY_USED = "used"

    private fun today(): String = SimpleDateFormat("yyyyMMdd", Locale.US).format(Date())

    private fun used(context: Context): Int {
        val prefs = context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        return if (prefs.getString(KEY_DAY, null) == today()) prefs.getInt(KEY_USED, 0) else 0
    }

    fun remaining(context: Context): Int = (FREE_DAILY_LIMIT - used(context)).coerceAtLeast(0)

    fun registerUse(context: Context) {
        val prefs = context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        prefs.edit()
            .putString(KEY_DAY, today())
            .putInt(KEY_USED, used(context) + 1)
            .apply()
    }
}
