Create a PHP 8.4 Composer library in this folder that splits an amount of money between several parties.

Autoload the namespace `Acme\Billing\` from `src/` with PSR-4, and put the logic in the class `Acme\Billing\Allocator`, method `public static function split(int $cents, array $weights): array`. `$weights` maps each party (any array key) to a non-negative integer weight; the result has the same keys in the same order, each with a whole number of cents proportional to its weight, and the cents always add up to `$cents` exactly. Each share is first rounded down; the cents left over then go one each to the parties whose rounding dropped the largest fraction, the earliest key first on a tie.

Throw an `InvalidArgumentException` for a negative `$cents`, an empty `$weights`, a weight that is not an `int` (a string or a float included) or is negative, and weights that add up to zero. Test it with PHPUnit.

Work autonomously: nobody will answer questions.
