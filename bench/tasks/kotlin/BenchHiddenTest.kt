package com.example.csv

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Test

class BenchHiddenTest {
    @Test
    fun `plain fields are split on commas`() {
        assertEquals(listOf("a", "b", "c"), parseCsvLine("a,b,c"))
    }

    @Test
    fun `a line without a comma is one field`() {
        assertEquals(listOf("abc"), parseCsvLine("abc"))
    }

    @Test
    fun `an empty line is one empty field`() {
        assertEquals(listOf(""), parseCsvLine(""))
    }

    @Test
    fun `empty fields are kept`() {
        assertEquals(listOf("a", "", "b"), parseCsvLine("a,,b"))
    }

    @Test
    fun `a trailing comma gives a trailing empty field`() {
        assertEquals(listOf("a", ""), parseCsvLine("a,"))
    }

    @Test
    fun `a lone comma gives two empty fields`() {
        assertEquals(listOf("", ""), parseCsvLine(","))
    }

    @Test
    fun `spaces are part of the field`() {
        assertEquals(listOf(" a ", "b "), parseCsvLine(" a ,b "))
    }

    @Test
    fun `a quoted field may contain commas`() {
        assertEquals(listOf("a,b", "c"), parseCsvLine("\"a,b\",c"))
    }

    @Test
    fun `a doubled quote inside a quoted field is one quote`() {
        assertEquals(listOf("say \"hi\"", "x"), parseCsvLine("\"say \"\"hi\"\"\",x"))
    }

    @Test
    fun `an empty quoted field is an empty field`() {
        assertEquals(listOf("", "a", ""), parseCsvLine("\"\",a,\"\""))
    }

    @Test
    fun `a quoted field made of one doubled quote is a quote`() {
        assertEquals(listOf("\""), parseCsvLine("\"\"\"\""))
    }

    @Test
    fun `an unterminated quoted field throws`() {
        assertThrows(IllegalArgumentException::class.java) { parseCsvLine("\"abc,d") }
    }

    @Test
    fun `a field ending in an escaped quote without a closing quote throws`() {
        assertThrows(IllegalArgumentException::class.java) { parseCsvLine("\"abc\"\"") }
    }

    @Test
    fun `a quote inside an unquoted field throws`() {
        assertThrows(IllegalArgumentException::class.java) { parseCsvLine("a\"b,c") }
    }

    @Test
    fun `a character after a closing quote throws`() {
        assertThrows(IllegalArgumentException::class.java) { parseCsvLine("\"a\"b,c") }
    }

    @Test
    fun `a space after a closing quote throws`() {
        assertThrows(IllegalArgumentException::class.java) { parseCsvLine("\"a\" ,c") }
    }
}
