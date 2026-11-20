<?php

declare(strict_types=1);

namespace Acme\Billing;

use InvalidArgumentException;

final class Allocator
{
    /**
     * Split $cents between the keys of $weights in proportion to their weights (largest remainder method).
     *
     * shortcut: $cents * weight must fit in an int, enough for invoice amounts; use bcmath beyond PHP_INT_MAX.
     *
     * @param array<array-key, mixed> $weights
     * @return array<array-key, int> the shares, keyed and ordered like $weights
     */
    public static function split(int $cents, array $weights): array
    {
        if ($cents < 0) {
            throw new InvalidArgumentException("Cents must not be negative, got {$cents}.");
        }
        if ($weights === []) {
            throw new InvalidArgumentException('Weights must not be empty.');
        }
        $checked = [];
        foreach ($weights as $key => $weight) {
            if (!is_int($weight) || $weight < 0) {
                throw new InvalidArgumentException("Weight of party {$key} must be a non-negative int.");
            }
            $checked[$key] = $weight;
        }
        $total = array_sum($checked);
        if ($total === 0) {
            throw new InvalidArgumentException('Weights must not add up to zero.');
        }

        $shares = [];
        $remainders = [];
        $left = $cents;
        foreach ($checked as $key => $weight) {
            $shares[$key] = intdiv($cents * $weight, $total);
            $remainders[$key] = $cents * $weight % $total;
            $left -= $shares[$key];
        }
        // arsort is stable since PHP 8.0, so equal remainders keep the order of the keys.
        arsort($remainders);
        foreach (array_slice(array_keys($remainders), 0, $left) as $key) {
            $shares[$key]++;
        }

        return $shares;
    }
}
