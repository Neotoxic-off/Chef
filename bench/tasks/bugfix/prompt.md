Bulk discount lost when I add the same product in two steps

Hi, a customer complained about our shop cart (the code in this folder) and I could reproduce it.

Steps:
1. Add 6 stoneware mugs (SKU `MUG-01`, 12.00 each) to the cart.
2. Add 4 more of the same mug.
3. Look at the totals.

Expected: the cart holds 10 mugs, so it gets the 10% bulk discount (-12.00), exactly like when I add 10 mugs at once.

Actual: no bulk discount at all. The subtotal is right (120.00), but the discount line is missing and the customer pays 12.00 more plus tax.

It gets worse: if I then change the mug quantity to 12 in the cart, the cart says 16 items instead of 12.

Can you fix it?

Work autonomously: nobody will answer questions.
