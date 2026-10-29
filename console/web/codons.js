// Genetic code and text -> codon conversion. Plain script (no modules) so index.html also works from file://.
(function () {
  const BASES = "TCAG";
  // Standard genetic code, codon order T,C,A,G (first base outermost, third base innermost).
  const AA_STRING = "FFLLSSSSYY**CC*WLLLLPPPPHHQQRRRRIIIMTTTTNNKKSSRRVVVVAAAADDEEGGGG";
  const AA_NAMES = {
    F: "Phe", L: "Leu", S: "Ser", Y: "Tyr", C: "Cys", W: "Trp", P: "Pro", H: "His", Q: "Gln", R: "Arg",
    I: "Ile", M: "Met", T: "Thr", N: "Asn", K: "Lys", V: "Val", A: "Ala", D: "Asp", E: "Glu", G: "Gly",
    "*": "Stop",
  };

  const CODON_TABLE = {};   // "ATG" -> "M"
  const AA_CODONS = {};     // "M" -> ["ATG"]
  let n = 0;
  for (const a of BASES) for (const b of BASES) for (const c of BASES) {
    const codon = a + b + c;
    const aa = AA_STRING[n++];
    CODON_TABLE[codon] = aa;
    (AA_CODONS[aa] = AA_CODONS[aa] || []).push(codon);
  }
  // Put the commonly used codon first so each letter has a sensible default (stop = TAA, as on the silkscreen).
  const PREFERRED = { "*": "TAA", M: "ATG", W: "TGG" };
  for (const aa of Object.keys(AA_CODONS)) {
    const pref = PREFERRED[aa];
    if (pref) AA_CODONS[aa] = [pref, ...AA_CODONS[aa].filter((x) => x !== pref)];
  }

  const COMP = { A: "T", T: "A", G: "C", C: "G" };
  const complement = (b) => COMP[b] || "-";

  function normalizeCodon(text) {
    const s = String(text).toUpperCase().replace(/U/g, "T");
    return /^[ATGC]{3}$/.test(s) ? s : null;
  }

  // Mode "amino": one-letter amino acid code -> codon (choice picks a synonymous codon).
  // Mode "ascii6": ASCII 0x20..0x5F (space .. "_", letters case-folded) -> 6 bits -> 3 bases, 2 bits each.
  const ASCII6_BASES = "ACGT";
  function charToCodon(ch, mode, choice) {
    if (mode === "amino") {
      const u = ch.toUpperCase();
      if (u === " " ) return { ch, codon: null, kind: "blank", note: "空白" };
      const key = u === "." ? "*" : u;
      const list = AA_CODONS[key];
      if (!list) return { ch, codon: null, kind: "none", note: "対応なし" };
      const codons = list;
      const codon = codons[((choice || 0) % codons.length + codons.length) % codons.length];
      return { ch, codon, aa: key, kind: "ok", options: codons.length };
    }
    const code = ch.toUpperCase().charCodeAt(0);
    if (ch.length === 0 || code < 0x20 || code > 0x5f) return { ch, codon: null, kind: "none", note: "対応なし" };
    const v = code - 0x20;
    const codon = ASCII6_BASES[(v >> 4) & 3] + ASCII6_BASES[(v >> 2) & 3] + ASCII6_BASES[v & 3];
    return { ch, codon, aa: CODON_TABLE[codon], kind: "ok", options: 1 };
  }

  window.CODONS = {
    BASES, CODON_TABLE, AA_CODONS, AA_NAMES, complement, normalizeCodon, charToCodon,
    aaOf: (codon) => CODON_TABLE[codon] || null,
    allCodons: () => Object.keys(CODON_TABLE),
  };
})();
