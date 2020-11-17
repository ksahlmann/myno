#ifndef LZSS_H

#define LZSS_H

extern void lzss_set_output(unsigned char *buf, int buf_len);
extern void lzss_set_input(unsigned char *buf, int buf_len);
extern int lzss_encode(void);
extern int lzss_decode(void);

#endif
