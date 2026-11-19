Create a TypeScript command-line tool in this folder that converts a human duration such as `1h30m` into milliseconds: it prints the total, or prints why the input is invalid and exits with code 1.

Put the logic in a module `src/duration.ts` exporting `parseDuration(text: string): number`, which returns the total in milliseconds or throws an `Error` saying why the input is invalid. Surrounding whitespace is ignored. The rest is one or more parts written together with no separator, each a whole number of digits followed by a unit: `d`, `h`, `m`, `s` or `ms`. Each unit appears at most once, from the largest to the smallest (`1h30m` is valid, `30m1h` and `1h1h` are not). Signs, decimals, spaces between parts and unknown units are invalid. The total must be greater than 0 and at most 30 days.

Work autonomously: nobody will answer questions.
