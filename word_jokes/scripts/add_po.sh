# 1) Analyze all words with Hunspell (morphology)
#    Input:  hu_50k.cleaned.txt  (one word per line, UTF-8)
#    Output: po.map  (word \t comma_separated_po_tags)
hunspell -d hu_HU -m < hu_50k.cleaned.txt | \
awk '
{
  w = $1
  for (i=2; i<=NF; i++) {
    if ($i ~ /^po:/) {
      split($i, a, ":")
      tag = a[2]
      k = w SUBSEP tag
      if (!(k in seen)) {
        seen[k] = 1
        if (tags[w] != "") tags[w] = tags[w] "," tag
        else tags[w] = tag
      }
    }
  }
}
END {
  for (w in tags) print w "\t" tags[w]
}
' > po.map

# 2) Merge back in original order: word \t po_tags (or UNK if no tag found)
awk -F'\t' 'NR==FNR { map[$1]=$2; next } { t = map[$1]; if (t=="") t="UNK"; print $1 "\t" t }' \
  po.map hu_50k.cleaned.txt > hu_50k.with_pos.tsv
