/* LZSS encoder-decoder (Haruhiko Okumura; public domain) */

#define EOF (-1)

#define EI 11  /* typically 10..13 */
#define EJ  4  /* typically 4..5 */
#define P   1  /* If match length <= P then output one character */
#define N (1 << EI)  /* buffer size */
#define F ((1 << EJ) + 1)  /* lookahead buffer size */

static int buf, mask = 0; // getbit()
static int bit_buffer = 0, bit_mask = 128;
static unsigned long codecount = 0, textcount = 0;
static unsigned char buffer[N * 2];

static unsigned char *outbuf;
static int outbuf_len;
static int outbuf_i;

static unsigned char *inbuf;
static int inbuf_len;
static int inbuf_i;

static void reset_variable() {
    buf = 0;
    mask = 0;
    bit_buffer = 0;
    bit_mask = 128;
    codecount = 0;
    textcount = 0;
}

void lzss_set_output(unsigned char *buf, int buf_len) {
    outbuf = buf;
    outbuf_len = buf_len;
    outbuf_i = 0;
}

void lzss_set_input(unsigned char *buf, int buf_len) {
    inbuf = buf;
    inbuf_len = buf_len;
    inbuf_i = 0;
}

static int put_out(int c) {
    if (outbuf_i < outbuf_len) {
        unsigned char d = c;
        outbuf[outbuf_i++] = d;
        return d;
    } else {
        return EOF;
    }
}

static int get_in() {
    if (inbuf_i < inbuf_len) {
        return inbuf[inbuf_i++];
    } else {
        return EOF;
    }
}

static int putbit1(void)
{
    bit_buffer |= bit_mask;
    if ((bit_mask >>= 1) == 0) {
        if (put_out(bit_buffer) == EOF) return EOF;
        bit_buffer = 0;  bit_mask = 128;  codecount++;
    }

    return 0;
}

static int putbit0(void)
{
    if ((bit_mask >>= 1) == 0) {
        if (put_out(bit_buffer) == EOF) return EOF;
        bit_buffer = 0;  bit_mask = 128;  codecount++;
    }

    return 0;
}

static int flush_bit_buffer(void)
{
    if (bit_mask != 128) {
        if (put_out(bit_buffer) == EOF) return EOF;
        codecount++;
    }

    return 0;
}

static int output1(int c)
{
    int mask;

    putbit1();
    mask = 256;
    while (mask >>= 1) {
        if (c & mask) {
            if (putbit1()) {
                return EOF;
            }
        } else {
            if (putbit0()) {
                return EOF;
            }
        }
    }

    return 0;
}

static int output2(int x, int y)
{
    int mask;

    putbit0();
    mask = N;
    while (mask >>= 1) {
        if (x & mask) {
            if (putbit1())
                return EOF;
        } else {
            if (putbit0())
                return EOF;
        }
    }
    mask = (1 << EJ);
    while (mask >>= 1) {
        if (y & mask) {
            if (putbit1())
                return EOF;
        } else {
            if (putbit0())
                return EOF;
        }
    }

    return 0;
}

int lzss_encode(void)
{
    int i, j, f1, x, y, r, s, bufferend, c;

    reset_variable();

    for (i = 0; i < N - F; i++) buffer[i] = ' ';
    for (i = N - F; i < N * 2; i++) {
        if ((c = get_in()) == EOF) break;
        buffer[i] = c;  textcount++;
    }
    bufferend = i;  r = N - F;  s = 0;
    while (r < bufferend) {
        f1 = (F <= bufferend - r) ? F : bufferend - r;
        x = 0;  y = 1;  c = buffer[r];
        for (i = r - 1; i >= s; i--)
            if (buffer[i] == c) {
                for (j = 1; j < f1; j++)
                    if (buffer[i + j] != buffer[r + j]) break;
                if (j > y) {
                    x = i;  y = j;
                }
            }
        if (y <= P) {
            y = 1;
            int q = output1(c);
            if (q) return q;
        } else {
            int q = output2(x & (N - 1), y - 2);
            if (q) return q;
        }

        r += y;  s += y;
        if (r >= N * 2 - F) {
            for (i = 0; i < N; i++) buffer[i] = buffer[i + N];
            bufferend -= N;  r -= N;  s -= N;
            while (bufferend < N * 2) {
                if ((c = get_in()) == EOF) break;
                buffer[bufferend++] = c;  textcount++;
            }
        }
    }

    if (flush_bit_buffer())
        return EOF;

    return codecount;
}

static int getbit(int n) /* get n bits */
{
    int i, x;

    x = 0;
    for (i = 0; i < n; i++) {
        if (mask == 0) {
            if ((buf = get_in()) == EOF) return EOF;
            mask = 128;
        }
        x <<= 1;
        if (buf & mask) x++;
        mask >>= 1;
    }
    return x;
}

int lzss_decode(void)
{
    int i, j, k, r, c;

    reset_variable();

    for (i = 0; i < N - F; i++) buffer[i] = ' ';
    r = N - F;
    while ((c = getbit(1)) != EOF) {
        if (c) {
            if ((c = getbit(8)) == EOF) break;
            put_out(c);
            buffer[r++] = c;  r &= (N - 1);
        } else {
            if ((i = getbit(EI)) == EOF) break;
            if ((j = getbit(EJ)) == EOF) break;
            for (k = 0; k <= j + 1; k++) {
                c = buffer[(i + k) & (N - 1)];
                put_out(c);
                buffer[r++] = c;  r &= (N - 1);
            }
        }
    }

    return outbuf_i;
}
