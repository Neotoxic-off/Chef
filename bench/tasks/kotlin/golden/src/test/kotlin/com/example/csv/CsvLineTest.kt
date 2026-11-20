package com.example.csv

import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith

class CsvLineTest {
    @Test
    fun `fields are split on commas`() {
        assertEquals(listOf("a", "b"), parseCsvLine("a,b"))
    }

    @Test
    fun `an empty line is one empty field`() {
        assertEquals(listOf(""), parseCsvLine(""))
    }

    @Test
    fun `empty fields between and after commas are kept`() {
        assertEquals(listOf("a", "", "b", ""), parseCsvLine("a,,b,"))
    }

    @Test
    fun `a quoted field keeps its commas and spaces`() {
        assertEquals(listOf(" a, b ", "c"), parseCsvLine("\" a, b \",c"))
    }

    @Test
    fun `a doubled quote in a quoted field is one quote`() {
        assertEquals(listOf("a\"b"), parseCsvLine("\"a\"\"b\""))
    }

    @Test
    fun `an unterminated quoted field throws`() {
        assertFailsWith<IllegalArgumentException> { parseCsvLine("\"a,b") }
    }

    @Test
    fun `a quote inside an unquoted field throws`() {
        assertFailsWith<IllegalArgumentException> { parseCsvLine("a\"b") }
    }

    @Test
    fun `a character after a closing quote throws`() {
        assertFailsWith<IllegalArgumentException> { parseCsvLine("\"a\"b") }
    }
}
