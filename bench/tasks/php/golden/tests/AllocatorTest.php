<?php

declare(strict_types=1);

namespace Acme\Billing\Tests;

use Acme\Billing\Allocator;
use InvalidArgumentException;
use PHPUnit\Framework\Attributes\DataProvider;
use PHPUnit\Framework\TestCase;

final class AllocatorTest extends TestCase
{
    /** @return iterable<string, array{int, array<array-key, int>, array<array-key, int>}> */
    public static function splits(): iterable
    {
        yield 'even' => [90, [1, 1, 1], [30, 30, 30]];
        yield 'leftover to the first on a tie' => [100, [1, 1, 1], [34, 33, 33]];
        yield 'leftover to the largest dropped fraction' => [5, [2, 1], [3, 2]];
        yield 'string keys keep their order' => [10, ['b' => 3, 'a' => 1], ['b' => 8, 'a' => 2]];
        yield 'zero weight gets nothing' => [7, ['x' => 0, 'y' => 1, 'z' => 1], ['x' => 0, 'y' => 4, 'z' => 3]];
        yield 'zero cents' => [0, [1, 2], [0, 0]];
    }

    /**
     * @param array<array-key, int> $weights
     * @param array<array-key, int> $expected
     */
    #[DataProvider('splits')]
    public function testSplitsByWeight(int $cents, array $weights, array $expected): void
    {
        $shares = Allocator::split($cents, $weights);

        self::assertSame($expected, $shares);
        self::assertSame($cents, array_sum($shares));
    }

    /** @return iterable<string, array{int, array<array-key, mixed>}> */
    public static function invalidArguments(): iterable
    {
        yield 'negative cents' => [-1, [1]];
        yield 'no weights' => [10, []];
        yield 'negative weight' => [10, [1, -1]];
        yield 'float weight' => [10, [1, 1.5]];
        yield 'numeric string weight' => [10, [1, '2']];
        yield 'weights add up to zero' => [10, [0, 0]];
    }

    /** @param array<array-key, mixed> $weights */
    #[DataProvider('invalidArguments')]
    public function testRejectsInvalidArguments(int $cents, array $weights): void
    {
        $this->expectException(InvalidArgumentException::class);

        Allocator::split($cents, $weights);
    }
}
