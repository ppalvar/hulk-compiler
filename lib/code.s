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

print:
    lw $a0, 0($sp)
    li $v0, 4
    syscall
	la $a0, __newline__
	syscall
    jr $ra

boolToString:
    lw $t0, 0($sp) 
    beq $t0, $zero, is_false
    la $v0, __true__
    jr $ra
	is_false:
    la $v0, __false__
    jr $ra

numberToString:
    lwc1 $f12, 0($sp)

    cvt.w.s $f12, $f12
    mfc1 $t0, $f12

    li $a0, 12
	li $v0, 9
	syscall

    move $a0, $v0
    la $a1, format
    move $a2, $t0

	move $t0, $v0

	addi $sp, $sp, -4
	sw $ra, 0($sp)
	
	jal push_all
    jal sprintf
	jal pop_all
	
	lw $ra, 0($sp)
	addi $sp, $sp, 4


    move $v0, $t0
    jr $ra

.text
.globl concat_strings

concat_strings:
    # Load arguments from the stack
    lw $a0, 8($sp)  # Load the first string address
    lw $a1, 4($sp)  # Load the second string address
    lw $a2, 0($sp)  # Load the boolean value

    # Calculate the length of the first string
    move $t1, $a0  # Save the first string address to $t1
    concat_strings_loop1:
        lb $t2, 0($t1)  # Load a byte from the first string
        beqz $t2, concat_strings_end_loop1  # If byte is zero, go to concat_strings_end_loop1
        addiu $t1, $t1, 1  # Increment the first string address
        j concat_strings_loop1
    concat_strings_end_loop1:
        subu $t1, $t1, $a0  # Calculate the length of the first string

    # Calculate the length of the second string
	move $s2, $t2
    move $t2, $a1  # Save the second string address to $t2
    concat_strings_loop2:
        lb $t3, 0($t2)  # Load a byte from the second string
        beqz $t3, concat_strings_end_loop2  # If byte is zero, go to concat_strings_end_loop2
        addiu $t2, $t2, 1  # Increment the second string address
        j concat_strings_loop2
    concat_strings_end_loop2:
        subu $t2, $t2, $a1  # Calculate the length of the second string

    # Calculate the total length
    addu $a3, $t1, $t2  # Add the lengths of the two strings
    addiu $a3, $a3, 2  # Add one for the null terminator
    bnez $a2, concat_strings_add_space  # If boolean is non-zero, go to concat_strings_add_space
    j concat_strings_alloc
    concat_strings_add_space:
        addiu $a3, $a3, 1  # Add one for the space

    # Allocate memory for the buffer
    concat_strings_alloc:
		move $s0, $a0
		move $a0, $a3
        li $v0, 9  # syscall number for sbrk
        syscall
        move $t1, $v0  # Save the buffer address to $t1
		move $a0, $s0

    # Copy the first string to the buffer
    concat_strings_loop3:
        lb $t2, 0($a0)  # Load a byte from the first string
        beqz $t2, concat_strings_check_space  # If byte is zero, go to concat_strings_check_space
        sb $t2, 0($t1)  # Store the byte to the buffer
        addiu $a0, $a0, 1  # Increment the first string address
        addiu $t1, $t1, 1  # Increment the buffer address
        j concat_strings_loop3

    # Check if a space is needed
    concat_strings_check_space:
        beqz $a2, concat_strings_loop4  # If boolean is zero, go to concat_strings_loop4
        li $t2, 32  # ASCII for space
        sb $t2, 0($t1)  # Store the space to the buffer
        addiu $t1, $t1, 1  # Increment the buffer address

    # Copy the second string to the buffer
    concat_strings_loop4:
        lb $t2, 0($a1)  # Load a byte from the second string
        beqz $t2, concat_strings_end  # If byte is zero, go to concat_strings_end
        sb $t2, 0($t1)  # Store the byte to the buffer
        addiu $a1, $a1, 1  # Increment the second string address
        addiu $t1, $t1, 1  # Increment the buffer address
        j concat_strings_loop4

    concat_strings_end:
        # Null-terminate the buffer
        sb $zero, 0($t1)

        # Return
        jr $ra


#______________________________________________________________________________________________

sprintf:
	
	addi $sp, $sp, -24
	sw $ra, 0($sp)
	sw $s0, 4($sp)
	sw $s1, 8($sp)
	sw $s2, 12($sp)
	sw $s3, 16($sp)
	sw $sp, 20($sp)

	sw $a2, 32($sp)
	sw $a3, 36($sp)


	add $s0, $a0, $0
	add $s2, $a1, $0
	add $s3, $0, $0
	
	add	$s1, $sp, $0
	addi	$s1, $s1, 32 #beginning of the replacement args ($a2)
	
	lb $s3, 0($s2)
  

loop:
	beq $s3, $0, null				#is it terminating? (NULL in ascii is 0) -> null
	beq $s3, '%', percent		#is it % ? -> percent
	sb $s3, 0($s0)					#add it to the resulting string
	addi $s0, $s0, 1				#increment output pointer
	j nchar							#get next character -> nchar

nchar:
	addi $s2, $s2, 1				#look at the next character in the format string
	lb $s3, 0($s2)					#take that character and make it the current character
	j loop							#go back to the caller

null:
	sb $0, 0($s0)					#add it to resulting string
										#reload saved registers
	lw $ra, 0($sp)
	lw $s0, 4($sp)
	lw $s1, 8($sp)
	lw $s2, 12($sp)
	lw $s3, 16($sp)
	lw $sp, 20($sp)
	addi $sp, $sp, 24 			#restore stack ptr
	jr $ra

percent:
		addi $s2, $s2, 1			#look at the next character in the format string
		lb $s3, 0($s2)				#take that character and make it the current character

		bne $s3, 'b', tod			#is it b?
				lw $a0, 0($s1)

#				li $v0, 4
#				syscall
				jal bin
				addi $s1, $s1, 4
				j nchar
tod:	bne $s3, 'd', tou			#is it d?
				lw $a0, 0($s1)
				addi $s1, $s1, 4
				bgez	$a0, pos
				addi $t0, $0, '-'
				sb $t0, 0($s0)
				addi $s0, $s0, 1
				neg $a0, $a0
pos:			jal dec
				j nchar			
tou:	bne $s3, 'u', tox			#is it u?
				lw $a0, 0($s1)
				addi $s1, $s1, 4
				jal dec
				j nchar	

	#			lw $a0, 0($s1)
	#			addi $s1, $s1, 4
	#			jal uns
	#			j nchar	
tox:	bne $s3, 'x', too			#is it x?
				lw $a0, 0($s1)
				addi $s1, $s1, 4
				jal hex
				j nchar	
too:	bne $s3, 'o', toc			#is it o?

				lw $a0, 0($s1)


#				li $v0, 4
#				syscall

				jal oct
				addi $s1, $s1, 4
				j nchar	
		
toc:	bne $s3, 'c', tos			#is it c?
			lw $t0, 0($s1)			#put arg into a temporary register
			addi $s1, $s1, 4		#increment pointer to next arg
			sb $t0, 0($s0)			#put the char on the output string
			addi	$s0, $s0, 1		#increment pointer for output string
			j nchar

tos:	bne $s3, 's', top			#is it s?
			lw	$t0, 0($s1)			#put arg into a temporary register
			addi	$s1, $s1, 4		#increment pointer to next arg
			lb	$t1, 0($t0)			#load the first byte of the word
		strl:			
			beq	$t1, $0, strd	#if the byte contains '/0' then end
			sb	$t1, 0($s0)			#put the non-terminating char on the output string
			addi	$s0, $s0, 1		#increment pointer for output string
			addi	$t0, $t0, 1		#point to next byte in the word
			lb	$t1, 0($t0)			#get next byte in the word
			j	strl					#loop
		strd:
			j	nchar					#next char in format array

top:	bne $s3, '%', na			#is it %?
		addi $t0, $0, '%'
		sb $t0, 0($s0)
		addi $s0, $s0, 1
		j nchar
na:									
	sb $s3, 0($s0)
	addi $s0, $s0, 1
	j nchar

#This does the number backward (does not use the stack)
#bin:	addi $sp,$sp,-4
#		sw $ra, 0($sp)
#		
#nbin:	beq $a0, $0, endbin
#		remu $t0, $a0, 2
#		divu $a0, $a0, 2
#		addi $t0,$t0,'0'
#		sb $t0, 0($s0)
#		addi $s0, $s0, 1
#		j nbin
#endbin:
#		lw	$ra,0($sp)	# restore return address
#		addi	$sp,$sp, 4	# restore stack
#		jr	$ra		# return	




bin:	addi	$sp,$sp,-8	# get 2 words of stack
	sw	$ra,0($sp)	# store return address

	remu	$t0,$a0,2	# $t0 <- $a0 % 2
	addi	$t0,$t0,'0'	# $t0 += '0'
	divu	$a0,$a0,2	# $a0 /= 2
	beqz	$a0,onedigbin	# if( $a0 != 0 ) { 
	sw	$t0,4($sp)	#   save $t0 on our stack
	jal	bin		#   bin
	lw	$t0,4($sp)	#   restore $t0
	                        # } 
onedigbin:	sb	$t0, 0($s0)			#put the binary digit on the output string
			addi	$s0, $s0, 1		#increment pointer for output string
	lw	$ra,0($sp)	# restore return address
	addi	$sp,$sp, 8	# restore stack
	jr	$ra		# return

oct:	addi	$sp,$sp,-8	# get 2 words of stack
	sw	$ra,0($sp)	# store return address

	remu	$t0,$a0,8	# $t0 <- $a0 % 2
	addi	$t0,$t0,'0'	# $t0 += '0'
	divu	$a0,$a0,8	# $a0 /= 2
	beqz	$a0,onedigo	# if( $a0 != 0 ) { 
	sw	$t0,4($sp)	#   save $t0 on our stack
	jal	oct		#   oct
	lw	$t0,4($sp)	#   restore $t0
	                        # } 
onedigo:	sb	$t0, 0($s0)			#put the binary digit on the output string
			addi	$s0, $s0, 1		#increment pointer for output string
	lw	$ra,0($sp)	# restore return address
	addi	$sp,$sp, 8	# restore stack
	jr	$ra		# return


dec:	addi	$sp,$sp,-8	# get 2 words of stack
	sw	$ra,0($sp)	# store return address
	remu	$t0,$a0,10	# $t0 <- $a0 % 2
	addi	$t0,$t0,'0'	# $t0 += '0'
	divu	$a0,$a0,10	# $a0 /= 2
	beqz	$a0,onedigd	# if( $a0 != 0 ) { 
	sw	$t0,4($sp)	#   save $t0 on our stack
	jal	dec		#   oct
	lw	$t0,4($sp)	#   restore $t0
	                        # } 
onedigd:	sb	$t0, 0($s0)			#put the binary digit on the output string
			addi	$s0, $s0, 1		#increment pointer for output string
	lw	$ra,0($sp)	# restore return address
	addi	$sp,$sp, 8	# restore stack
	jr	$ra		# return


hex:	addi	$sp,$sp,-8	# get 2 words of stack
		sw	$ra,0($sp)	# store return address
		remu	$t0,$a0,16	# $t0 <- $a0 % 2
		ble	$t0,9, nine
		addi	$t0, $t0, 7

nine:	addi	$t0,$t0,'0'	# $t0 += '0'
		divu	$a0,$a0,16	# $a0 /= 2
		beqz	$a0,onedigh	# if( $a0 != 0 ) { 
		sw	$t0,4($sp)	#   save $t0 on our stack
		jal	hex		#   oct
		lw	$t0,4($sp)	#   restore $t0
	                        # } 
onedigh:	sb	$t0, 0($s0)			#put the binary digit on the output string
			addi	$s0, $s0, 1		#increment pointer for output string
	lw	$ra,0($sp)	# restore return address
	addi	$sp,$sp, 8	# restore stack
	jr	$ra		# return


















#oct:	addi	$sp,$sp,-8	# get 2 words of stack
#	sw	$ra,0($sp)	# store return address
#
#	remu	$t0,$a0,8	
#	addi	$t0,$t0,'0'	
#	divu	$a0,$a0,8	
#	beqz	$a0,onedigoct	 
#	sw	$t0,4($sp)	
#	jal	oct		
#	lw	$t0,4($sp)	
#	                
#onedigoct:	sb	$t1, 0($s0)			#put the octal digit on the output string
#			addi	$s0, $s0, 1		#increment pointer for output string
#	lw	$ra,0($sp)	# restore return address
#	addi	$sp,$sp, 8	# restore stack
#	jr	$ra		# return










#hex:	addi	$sp,$sp,-8	# get 2 words of stack
#	sw	$ra,0($sp)	# store return address
#
#	remu	$t0,$a0,16	
#	addi	$t0,$t0,'0'	
#	divu	$a0,$a0,16	
#	beqz	$a0,onedighex	 
#	sw	$t0,4($sp)	
#	jal	hex		
#	lw	$t0,4($sp)	
#	                
#onedighex:	sb	$t1, 0($s0)			#put the hex digit on the output string
#			addi	$s0, $s0, 1		#increment pointer for output string
#	lw	$ra,0($sp)	# restore return address
#	addi	$sp,$sp, 8	# restore stack
#	jr	$ra		# return
#
#dec:	addi	$sp,$sp,-8	# get 2 words of stack
#	sw	$ra,0($sp)	# store return address
#
#	remu	$t0,$a0,10	
#	addi	$t0,$t0,'0'	
#	divu	$a0,$a0,10	
#	beqz	$a0,onedigdec	 
#	sw	$t0,4($sp)	
#	jal	dec		
#	lw	$t0,4($sp)	
#	                
#onedigdec:	sb	$t1, 0($s0)			#put the decimal digit on the output string
#			addi	$s0, $s0, 1		#increment pointer for output string
#	lw	$ra,0($sp)	# restore return address
#	addi	$sp,$sp, 8	# restore stack
#	jr	$ra		# return

uns:	addi	$sp,$sp,-8	# get 2 words of stack
	sw	$ra,0($sp)	# store return address

	remu	$t0,$a0,10	
	addi	$t0,$t0,'0'	
	divu	$a0,$a0,10	
	beqz	$a0,onediguns	 
	sw	$t0,4($sp)	
	jal	uns		
	lw	$t0,4($sp)	
	                
onediguns:	sb	$t1, 0($s0)			#put the unsigned digit on the output string
			addi	$s0, $s0, 1		#increment pointer for output string
	lw	$ra,0($sp)	# restore return address
	addi	$sp,$sp, 8	# restore stack
	jr	$ra		# return

#___________________________________________________________________________________________
