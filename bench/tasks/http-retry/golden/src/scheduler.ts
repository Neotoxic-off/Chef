/** The only way the client reads the clock or waits, so tests can run without real delays. */
export interface Scheduler {
  /** Milliseconds since the Unix epoch. */
  now(): number;
  sleep(milliseconds: number): Promise<void>;
}

export const systemScheduler: Scheduler = {
  now: (): number => Date.now(),
  sleep: (milliseconds: number): Promise<void> =>
    new Promise<void>((resolve: () => void): void => {
      setTimeout(resolve, milliseconds);
    }),
};
