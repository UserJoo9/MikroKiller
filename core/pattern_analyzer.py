import os

class PatternAnalyzer :

    def __init__ (self ,manual_samples =None ):
        self .manual_samples =manual_samples
        self .user_patterns =None
        self .pass_patterns =None
        self ._samples =[]

    def load_patterns (self ):

        try :
            if not self ._samples :
                if self .manual_samples :
                    self ._samples =[l .strip ()for l in self .manual_samples .split ('\n')if l .strip ()]
                elif os .path .exists ('samples.txt'):
                    with open ('samples.txt','r')as f :
                        self ._samples =[l .strip ()for l in f if l .strip ()]

            samples =self ._samples

            if not samples :
                return

            has_separator =':'in samples [0 ]

            if has_separator :

                usernames =[]
                passwords =[]

                for s in samples :
                    if ':'in s :
                        parts =s .split (':',1 )
                        usernames .append (parts [0 ])
                        passwords .append (parts [1 ])

                if usernames and len (usernames [0 ])>0 :
                    u_len =len (usernames [0 ])
                    self .user_patterns =[{}for _ in range (u_len )]

                    for u in usernames :
                        if len (u )==u_len :
                            for i ,char in enumerate (u ):
                                self .user_patterns [i ][char ]=self .user_patterns [i ].get (char ,0 )+1

                    for i in range (u_len ):
                        total =sum (self .user_patterns [i ].values ())
                        if total >0 :
                            for char in self .user_patterns [i ]:
                                self .user_patterns [i ][char ]/=total

                if passwords and len (passwords [0 ])>0 :
                    p_len =len (passwords [0 ])
                    self .pass_patterns =[{}for _ in range (p_len )]

                    for p in passwords :
                        if len (p )==p_len :
                            for i ,char in enumerate (p ):
                                self .pass_patterns [i ][char ]=self .pass_patterns [i ].get (char ,0 )+1

                    for i in range (p_len ):
                        total =sum (self .pass_patterns [i ].values ())
                        if total >0 :
                            for char in self .pass_patterns [i ]:
                                self .pass_patterns [i ][char ]/=total
            else :

                if samples and len (samples [0 ])>0 :
                    length =len (samples [0 ])
                    common_patterns =[{}for _ in range (length )]

                    for s in samples :
                        if len (s )==length :
                            for i ,char in enumerate (s ):
                                common_patterns [i ][char ]=common_patterns [i ].get (char ,0 )+1

                    for i in range (length ):
                        total =sum (common_patterns [i ].values ())
                        if total >0 :
                            for char in common_patterns [i ]:
                                common_patterns [i ][char ]/=total

                    self .user_patterns =common_patterns
                    self .pass_patterns =common_patterns

        except Exception as e :
            self .user_patterns =None
            self .pass_patterns =None

    def add_sample (self ,sample ):

        sample =sample .strip ()
        if not sample or sample in self ._samples :
            return
        self ._samples .append (sample )
        self .user_patterns =None
        self .pass_patterns =None
        self .load_patterns ()
