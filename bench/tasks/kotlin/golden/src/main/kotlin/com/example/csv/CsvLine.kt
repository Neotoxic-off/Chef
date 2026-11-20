package com.example.csv

private const val SEPARATOR = ','
private const val QUOTE = '"'

private class Field(val text: String, val end: Int)

/**
 * Splits one CSV line into its fields, empty ones included; an empty line is one empty field.
 *
 * @throws IllegalArgumentException for an unterminated quoted field, a quote inside an unquoted field,
 * or a character between a closing quote and the next comma.
 */
public fun parseCsvLine(line: String): List<String> {
    val fields = mutableListOf<String>()
    var start = 0
    while (true) {
        val field = if (line.getOrNull(start) == QUOTE) readQuoted(line, start) else readUnquoted(line, start)
        fields += field.text
        if (field.end == line.length) {
            return fields
        }
        start = field.end + 1
    }
}

private fun readUnquoted(
    line: String,
    start: Int,
): Field {
    val separator = line.indexOf(SEPARATOR, start)
    val end = if (separator < 0) line.length else separator
    val text = line.substring(start, end)
    require(QUOTE !in text) { "Quote inside an unquoted field at column ${start + text.indexOf(QUOTE) + 1}" }
    return Field(text, end)
}

private fun readQuoted(
    line: String,
    start: Int,
): Field {
    val text = StringBuilder()
    var index = start + 1
    while (index < line.length) {
        if (line[index] != QUOTE) {
            text.append(line[index])
            index += 1
        } else if (line.getOrNull(index + 1) == QUOTE) {
            text.append(QUOTE)
            index += 2
        } else {
            val end = index + 1
            require(end == line.length || line[end] == SEPARATOR) { "Character after a closing quote at column ${end + 1}" }
            return Field(text.toString(), end)
        }
    }
    throw IllegalArgumentException("Quoted field starting at column ${start + 1} has no closing quote")
}
