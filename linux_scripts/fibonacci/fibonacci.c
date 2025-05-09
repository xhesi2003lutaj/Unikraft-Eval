#include <stdio.h>
#include <time.h>

int fibonacci(int n) {
    if(n == 0) {
        return 0;
    } else if(n == 1) {
        return 1;
    } else {
        return (fibonacci(n-1) + fibonacci(n-2));
    }
}

int main() {
    struct timespec start, end;

    clock_gettime(CLOCK_MONOTONIC, &start);

    int n = 50;
    printf("Fibonacci of %d:\n\n", n);

    for(int i = 0; i < n; i++) {
        printf("%d ", fibonacci(i));
    }
    printf("\n");

    clock_gettime(CLOCK_MONOTONIC, &end);

    long elapsed_ns = (end.tv_sec - start.tv_sec) * 1000000000L +
                      (end.tv_nsec - start.tv_nsec);

    printf("Elapsed time: %ld nanoseconds\n", elapsed_ns);
    return 0;
}