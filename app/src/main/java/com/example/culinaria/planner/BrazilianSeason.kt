package com.example.culinaria.planner

import java.time.LocalDate

enum class BrazilianSeason(val label: String) {
    SUMMER("Verão"),
    AUTUMN("Outono"),
    WINTER("Inverno"),
    SPRING("Primavera");

    companion object {
        fun from(date: LocalDate): BrazilianSeason = when (date.monthValue * 100 + date.dayOfMonth) {
            in 1221..1231, in 101..319 -> SUMMER
            in 320..620 -> AUTUMN
            in 621..922 -> WINTER
            else -> SPRING
        }

        fun firstDayOfWeek(year: Int, week: Int): LocalDate =
            LocalDate.of(year, 1, 4)
                .with(java.time.temporal.IsoFields.WEEK_OF_WEEK_BASED_YEAR, week.toLong())
                .with(java.time.temporal.ChronoField.DAY_OF_WEEK, 1)
    }
}
