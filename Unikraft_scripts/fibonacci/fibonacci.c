#include <stdio.h>
#include <uk/plat/time.h>
#include <uk/print.h>

int fibbonacci(int n)
{
   if (n == 0)
   {
      return 0;
   }
   else if (n == 1)
   {
      return 1;
   }
   else
   {
      return (fibbonacci(n - 1) + fibbonacci(n - 2));
   }
}

int main()
{
   __nsec start = ukplat_monotonic_clock();
   int n = 30;

   printf("Fibbonacci of %d:\n\n", n);

   for (int i = 0; i < n; i++)
   {
      printf("%d ", fibbonacci(i));
   }
   printf("\n");
   __nsec end = ukplat_monotonic_clock();
   uk_pr_info("Elapsed time: %llu ns\n", (unsigned long long)(end - start));
   printf("Elapsed time: %llu ns\n", (unsigned long long)(end - start));
   printf("\n");
}