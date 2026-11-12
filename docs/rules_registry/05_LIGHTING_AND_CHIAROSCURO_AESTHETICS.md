# 05. ქიაროსკუროს განათებისა და ვიზუალური ესთეტიკის რეესტრი (Lighting & Chiaroscuro Aesthetics)

წყაროები: [Chiaroscuro - Wikipedia](https://en.wikipedia.org/wiki/Chiaroscuro), [Adorama Chiaroscuro Lighting](https://adorama.com/alc/chiaroscuro-lighting-technique/), [No Film School Chiaroscuro](https://nofilmschool.com/chiaroscuro-lighting).

## კატეგორია 1: ყოველთვის სავალდებულო კანონები (`TIER_1_INVARIANT_MANDATORY` — `FAIL`)
1. **`LT-T1-01` — ხელმოწერილი სტილის ტოკენი (`KP-V4-STYLE`):**
   - ყველა კადრის `start_frame_prompt` სავალდებულოდ შეიცავს `world_bible.style_anchor_token`-ს: `"Luminescent Chiaroscuro and Tactile Mythic Realism historical docudrama"`.
2. **`LT-T1-02` — ანტი-კომიქსური და ანტი-2.5D ფილტრი (`KP-NO-LOOP-BOILERPLATE`):**
   - კატეგორიულად აკრძალულია 2D კომიქსის კონტურები (`bold ink linework`, `comic book outlines`, `cel-shading`), პლასტმასის CGI სიპრიალე და ტექსტური წარწერები კადრში (`negative_prompt`-ით დაცული).
3. **`LT-T1-03` — განათების უწყვეტობა ერთ სცენაში (`CF-LIGHTING-CONTINUITY`):**
   - ერთსა და იმავე ლოკაციაში მიმდინარე გადაბმულ კადრებს უნდა ჰქონდეთ თანმიმდევრული განათების გარემო (`lighting_and_time`), რათა კადრების შეცვლისას დღე და ღამე შემთხვევით არ აირიოს.

## კატეგორია 2: სცენარზე მორგებული კანონზომიერი საზღვრები (`TIER_2_STORY_BOUNDED_DYNAMIC` — `FAIL` საზღვრებს გარეთ)
1. **`LT-T2-01` — სინათლისა და ჩრდილის კონტრასტის ბალანსი:**
   - **სცენარი მართავს:** საიდუმლო შეთქმულების სცენაში ჩრდილი მეტია, ხოლო ტრიუმფალურ ან ღია ბრძოლის სცენაში — ოქროსფერი სხივები.
   - **კანონის საზღვრები:** ყოველ პრომპტში აღწერილია როგორც თბილი მთავარი შუქის წყარო (Key/Rim Light: `amber`, `gold`, `candlelight`, `muzzle-flash`, `sunrise`), ისე ღრმა ჩრდილის ტონი (`slate`, `indigo`, `charcoal`, `chiaroscuro shadow`).

## კატეგორია 3: სარეკომენდაციო / თემატიკაზე მორგებული (`TIER_3_THEMATIC_ADVISORY` — `ADVISORY`)
1. **`LT-T3-01` — ატმოსფერული ნაწილაკები ეპოქის მიხედვით:**
   - საბრძოლო სცენებში: დენთის კვამლი, ნისლი და ნაპერწკლები; კაბინეტურ სცენებში: სინათლის სხივში მოცურავე მტვრის ნაწილაკები და სანთლის ციმციმი.
