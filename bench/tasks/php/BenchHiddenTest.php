<?php

declare(strict_types=1);

use Acme\Billing\Allocator;
use PHPUnit\Framework\TestCase;

// Plain test methods, no attributes or annotations: the agent may have picked any PHPUnit version.
final class BenchHiddenTest extends TestCase
{
    public function testEqualWeightsGiveTheLeftoverCentToTheFirstParty(): void
    {
        $this->assertSame([34, 33, 33], Allocator::split(100, [1, 1, 1]));
    }

    public function testLeftoverGoesToTheLargestDroppedFractionNotTheFirstParty(): void
    {
        $this->assertSame([3, 2], Allocator::split(5, [2, 1]));
        $this->assertSame([14, 29, 57], Allocator::split(100, [1, 2, 4]));
    }

    public function testKeysAndTheirOrderAreKeptAndTiesGoToTheEarliestKey(): void
    {
        $this->assertSame(['b' => 8, 'a' => 2], Allocator::split(10, ['b' => 3, 'a' => 1]));
    }

    public function testZeroWeightGetsNothing(): void
    {
        $this->assertSame(['x' => 0, 'y' => 4, 'z' => 3], Allocator::split(7, ['x' => 0, 'y' => 1, 'z' => 1]));
    }

    public function testSharesAddUpExactly(): void
    {
        $this->assertSame([301, 300, 300, 100], Allocator::split(1001, [3, 3, 3, 1]));
        $this->assertSame([0, 0], Allocator::split(0, [1, 2]));
        $this->assertSame([9], Allocator::split(9, [5]));
    }

    public function testInvalidArgumentsAreRejected(): void
    {
        $this->assertRejected(-1, [1]);
        $this->assertRejected(10, []);
        $this->assertRejected(10, [1, -1]);
        $this->assertRejected(10, [1, 1.5]);
        $this->assertRejected(10, [1, '2']);
        $this->assertRejected(10, [0, 0]);
    }

    /** @param array<array-key, mixed> $weights */
    private function assertRejected(int $cents, array $weights): void
    {
        try {
            Allocator::split($cents, $weights);
        } catch (InvalidArgumentException) {
            $this->addToAssertionCount(1);
            return;
        }
        $this->fail('split(' . $cents . ', ' . json_encode($weights) . ') did not throw InvalidArgumentException');
    }
}
