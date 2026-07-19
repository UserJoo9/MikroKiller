import random
import string

class VoucherGenerator :

    def __init__ (self ,pattern_analyzer =None ):
        self .pattern_analyzer =pattern_analyzer

    def luhn_checksum (self ,card_number ):

        digits =[int (x )for x in str (card_number )]
        odd_digits =digits [-1 ::-2 ]
        even_digits =digits [-2 ::-2 ]

        total =sum (odd_digits )
        for d in even_digits :
            total +=sum ([int (x )for x in str (d *2 )])

        return total %10 ==0

    def generate (self ,char_type ,min_len ,max_len ,start ,end ,contains ='',
    use_luhn =False ,is_password =False ,letter_case ='lowercase'):

        for _ in range (100 ):

            if self .pattern_analyzer :
                patterns =None
                if is_password and self .pattern_analyzer .pass_patterns :
                    patterns =self .pattern_analyzer .pass_patterns
                elif not is_password and self .pattern_analyzer .user_patterns :
                    patterns =self .pattern_analyzer .user_patterns

                if patterns :
                    v =''
                    for i in range (len (patterns )):
                        chars =list (patterns [i ].keys ())
                        weights =list (patterns [i ].values ())
                        if chars and weights :
                            v +=random .choices (chars ,weights =weights ,k =1 )[0 ]

                    if v :
                        res =v
                    else :
                        res =self ._generate_with_charset (
                        char_type ,min_len ,max_len ,start ,end ,contains ,letter_case
                        )
                else :
                    res =self ._generate_with_charset (
                    char_type ,min_len ,max_len ,start ,end ,contains ,letter_case
                    )
            else :
                res =self ._generate_with_charset (
                char_type ,min_len ,max_len ,start ,end ,contains ,letter_case
                )

            if not use_luhn :
                return res

            if self .luhn_checksum (res ):
                return res

        return res

    def _generate_with_charset (self ,char_type ,min_len ,max_len ,start ,end ,contains ,letter_case ):

        target_len =random .randint (min_len ,max_len )
        prefix_len =len (start )
        suffix_len =len (end )
        contains_len =len (contains )

        random_len =target_len -prefix_len -suffix_len

        if random_len <contains_len :
            # Clamp: return the longest possible string within target_len
            clamped = start + contains + end
            if len(clamped) > max_len:
                # Drop characters from the middle (contains) to fit
                over = len(clamped) - max_len
                mid = contains[:len(contains) - over]
                clamped = start + mid + end
            return clamped

        if char_type =='digits':
            chars =string .digits
        elif char_type =='letters':
            if letter_case =='lowercase':
                chars =string .ascii_lowercase
            elif letter_case =='uppercase':
                chars =string .ascii_uppercase
            else :
                chars =string .ascii_letters
        else :
            if letter_case =='lowercase':
                chars =string .ascii_lowercase +string .digits
            elif letter_case =='uppercase':
                chars =string .ascii_uppercase +string .digits
            else :
                chars =string .ascii_letters +string .digits

        rem_len =random_len -contains_len
        rem_chars =random .choices (chars ,k =rem_len )

        insert_idx =random .randint (0 ,rem_len )
        middle =rem_chars [:insert_idx ]+list (contains )+rem_chars [insert_idx :]

        return start +''.join (middle )+end
