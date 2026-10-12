data class TursoQueryRequest(
    val requests: List<TursoRequest>
)

data class TursoRequest(
    val type: String = "execute",
    val stmt: TursoStatement
)

data class TursoStatement(
    val sql: String,
    val args: List<TursoArg>? = null
)

data class TursoArg(
    val type: String,
    val value: Any?
)

data class TursoQueryResponse(
    val results: List<TursoResult>
)

data class TursoResult(
    val response: TursoResponse,
    val error: TursoError? = null
)

data class TursoResponse(
    val type: String,
    val result: TursoQueryResult
)

data class TursoQueryResult(
    val rows: List<List<TursoValue>>,
    val cols: List<TursoColumn>
)

data class TursoColumn(
    val name: String
)

data class TursoValue(
    val type: String,
    val value: Any?
) {
    fun asString(): String? = value?.toString()
    fun asInt(): Int? = (value as? Number)?.toInt()
    fun asLong(): Long? = (value as? Number)?.toLong()
    fun asDouble(): Double? = (value as? Number)?.toDouble()
    fun asBoolean(): Boolean = value == 1 || value == true
}

data class TursoError(
    val message: String
)