exit:
	li 		$v0, 10
	syscall

print_integer:
	li		$v0, 1 
	syscall
	jr		$ra

print_double:
	li		$v0, 2
	syscall
	jr		$ra

print_string:
	li		$v0, 4
	syscall
	jr		$ra

print_boolean:
    li      $v0, 4
    beq     $a0, $zero, print_false
print_true:
    la      $a0, __true__
    jr      print_boolean_end
print_false:
    la      $a0, __false__
print_boolean_end:
    syscall
    jr      $ra

print_undefined:
    li      $v0, 4
    la      $a0, __undefined__
    syscall
    jr      $ra

print_newline:
    li      $v0, 4
    la      $a0, __newline__
    syscall
    jr      $ra

push_all:
    addi    $sp,    $sp,   -92

    sw		$v0,	0($sp)
	sw		$t0,	4($sp)
	sw		$t1,	8($sp)
	sw		$t2,	12($sp)
	sw		$t3,	16($sp)
	sw		$t4,	20($sp)
	sw		$t5,	24($sp)
	sw		$t6,	28($sp)
	sw		$t7,	32($sp)
	sw		$t8,	36($sp)
	sw		$t9,    40($sp)
	sw		$s0,	44($sp)
	sw		$s1,	48($sp)
	sw		$s2,	52($sp)
	sw		$s3,	56($sp)
	sw		$s4,	60($sp)
    swc1    $f12,   64($sp)
    swc1    $f13,   68($sp)
    swc1    $f14,   72($sp)
    swc1    $f15,   76($sp)
    swc1    $f16,   80($sp)
    swc1    $f17,   84($sp)
    swc1    $f18,   88($sp)

    jr      $ra

pop_all:
    lw		$v0,	0($sp)
	lw		$t0,	4($sp)
	lw		$t1,	8($sp)
	lw		$t2,	12($sp)
	lw		$t3,	16($sp)
	lw		$t4,	20($sp)
	lw		$t5,	24($sp)
	lw		$t6,	28($sp)
	lw		$t7,	32($sp)
	lw		$t8,	36($sp)
	lw		$t9,    40($sp)
	lw		$s0,	44($sp)
	lw		$s1,	48($sp)
	lw		$s2,	52($sp)
	lw		$s3,	56($sp)
	lw		$s4,	60($sp)
    lwc1    $f12,   64($sp)
    lwc1    $f13,   68($sp)
    lwc1    $f14,   72($sp)
    lwc1    $f15,   76($sp)
    lwc1    $f16,   80($sp)
    lwc1    $f17,   84($sp)
    lwc1    $f18,   88($sp)

    addi    $sp,    $sp,   92
    jr      $ra