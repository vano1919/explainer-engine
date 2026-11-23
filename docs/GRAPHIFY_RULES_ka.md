# Graphify: გამოყენების წესები და გეგმა

**English summary (5 lines)**
1. Graphify (PyPI `graphifyy` 0.9.112) builds a local code graph; `--code-only` costs $0 and takes ~40 s on CPU (no RunPod).
2. Use it only for impact/path/explain questions on big refactors or unknown modules; plain "where is X" stays with grep.
3. Never run `graphify claude install` (edits CLAUDE.md, adds a hook and ~37k tokens per thread); no `graphify hook install` either.
4. Graph lives in `graphify-out/` of a throwaway checkout, never committed; refresh with `graphify update .` (~30 s).
5. The working thread may run it on its own for the triggers below; installing it permanently needs the creator's word. Evidence: `GRAPHIFY_VERDICT_ka.md`.

## 1. როდის ვუშვებთ (ღირს)
- **გავლენის ანალიზი** დიდ ცვლილებამდე: ფუნქცია/ფაილი, რომელსაც ბევრი გამომძახებელი აქვს (მაგ. `duck_gain()`, `write_json_atomic()`): `graphify affected "ფუნქცია()"`.
- **უცნობი მოდული**: როგორ არის დაკავშირებული ორი ნაწილი: `graphify path "A" "B"`; ერთი ფაილის გარემო: `graphify explain "run.py"`.
- **რეფაქტორინგი ან ბევრი ფაილის შეხება** (ტესტებიც გამომძახებლებში ჩანს).
- ჩვეულებრივ ერთ-ორ კითხვაზე იქნება საკმარისი; გრაფის აგება ერთხელ სრედში.

## 2. როდის არ ვუშვებთ
- ჩვეულებრივი ძებნა "სად არის X": `grep` / Grep ინსტრუმენტი (გრაფი ხმაურიანია და ზოგჯერ შეკვეცილია).
- **არასოდეს** `graphify claude install` (ცვლის CLAUDE.md-ს, ყოველ Grep/Glob-ზე hook, ~37 000 ტოკენი ყოველ სრედზე).
- არც `graphify hook install` (git hook-ები, +30 წმ ყოველ კომიტზე) და არც `graphify extract` ისე, რომ `--code-only` არ იყოს: ჩვენი docs/json/სურათები LLM გასაღებს და ფულს ითხოვს (დაუსტურებელია); ფასიანი გაშვება მხოლოდ შენი სიტყვით.
- `GRAPH_REPORT.md` არ წავიკითხოთ (150 კბ, უსახელო თემები).

## 3. ზუსტი ბრძანებები ($0, CPU, RunPod არ სჭირდება)
```bash
python3 -m venv /tmp/gvenv && /tmp/gvenv/bin/pip install -q graphifyy==0.9.112
cd <ცალკე checkout, მაგ. git worktree add ../ee-graph origin/systemic/next-video>
env -u ANTHROPIC_API_KEY -u GEMINI_API_KEY GRAPHIFY_BACKEND=none \
  /tmp/gvenv/bin/graphify extract . --code-only          # ~40 წმ, ~18 000 კვანძი
/tmp/gvenv/bin/graphify affected "duck_gain()"            # ან path / explain
/tmp/gvenv/bin/graphify update .                          # განახლება ცვლილების შემდეგ, ~30 წმ
```
გასაღებების გამორთვა სავალდებულოა: გარემოში `GEMINI_API_KEY` არსებობს და Graphify ავტომატურად მას აირჩევდა.

## 4. სად ცხოვრობს
`graphify-out/` (graph.json ~20 მბ) მხოლოდ დროებით checkout-ში, **არასოდეს იკომიტება** (არც GitHub-ზე, არც Drive-ზე, არც HF-ზე; გრაფი ძველდება ყოველ კომიტზე). შედარება ახლადობისთვის: `git rev-parse HEAD` vs გრაფის "Built from commit". სამუშაოს ბოლოს checkout წაიშლება (`git worktree remove`).

## 5. ვინ წყვეტს
- ზემოთ 1-ლი პუნქტის ტრიგერზე მომუშავე სრედი თავად უშვებს (ფასი $0, რეპოში არაფერი იცვლება).
- მუდმივი ჩართვა (CLAUDE.md, hooks, ფასიანი სემანტიკა) მხოლოდ შენი სიტყვით.
- ვერდიქტი და გაზომვები: `GRAPHIFY_VERDICT_ka.md`. თუ ახალი ვერსია გამოვა, გაზომვა თავიდან არ მეორდება, სანამ ტრიგერი არ გაჩნდება.
