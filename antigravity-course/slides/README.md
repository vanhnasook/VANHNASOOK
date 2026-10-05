# ສະໄລສອນ Antigravity

| ໄຟລ໌ | ຫຼັກສູດ | ຈຳນວນສະໄລ |
|---|---|---|
| [`Antigravity-Basic.pptx`](Antigravity-Basic.pptx) | Basic · 4 ຊົ່ວໂມງ (2 ມື້) | 35 |
| [`Antigravity-Advanced.pptx`](Antigravity-Advanced.pptx) | Advanced · 8 ຊົ່ວໂມງ (4 ມື້) | 43 |
| [`Antigravity-Basic.pdf`](Antigravity-Basic.pdf) | Basic (PDF ສຳລັບແຈກ ຫຼື ພິມ) | 35 |
| [`Antigravity-Advanced.pdf`](Antigravity-Advanced.pdf) | Advanced (PDF ສຳລັບແຈກ ຫຼື ພິມ) | 43 |

- ແບ່ງເປັນ Section ຕາມມື້ຮຽນ. ທຸກສະໄລບອກມື້, ເວລາ ແລະ ຫົວຂໍ້ ຢູ່ມຸມຊ້າຍເທິງ.
- ທຸກສະໄລມີ **Speaker Notes** ເປັນພາສາລາວ: ສິ່ງທີ່ຕ້ອງເວົ້າ, ກິດຈະກຳ ແລະ ເວລາ (ມີສະເພາະໃນ .pptx, ບໍ່ມີໃນ PDF).
- ສະໄລ Workshop ມີພື້ນສີເທົາ ແລະ ປ້າຍ WORKSHOP ສີເຫຼືອງ.
- ຄຳສັ່ງ (Prompt) ໃນສະໄລ ກົງກັບ [`../basic.md`](../basic.md) ແລະ [`../advanced.md`](../advanced.md).

## ຕິດຕັ້ງຟອນກ່ອນເປີດ

ສະໄລໃຊ້ຟອນ **Noto Sans Lao** ແລະ **Noto Sans Lao Looped**. ຕິດຕັ້ງ 4 ໄຟລ໌ໃນ [`fonts/`](fonts/) ກ່ອນ
(Windows: ຄລິກຂວາ → Install for all users). ຖ້າບໍ່ຕິດຕັ້ງ PowerPoint ຈະໃຊ້ຟອນລາວອື່ນແທນ ແລະ ບາງຂໍ້ຄວາມອາດລົ້ນກ່ອງ.
ຟອນເຫຼົ່ານີ້ໃຊ້ສັນຍາອະນຸຍາດ SIL Open Font License ([`fonts/OFL.txt`](fonts/OFL.txt)).

## ກ່ອນສອນ

- ແກ້ `[ຊື່ຜູ້ສອນ]`, `[ລິ້ງກຸ່ມ]` ແລະ `[020 XXXX XXXX]` ໃນສະໄລທຳອິດ ແລະ ສະໄລສຸດທ້າຍ.
- ກວດຊື່ເມນູ ແລະ ຂັ້ນຕອນຕິດຕັ້ງໃນ Antigravity ເວີຊັນປັດຈຸບັນ ເພາະ Google ອັບເດດເລື້ອຍ.
- ກຽມໄຟລ໌ຂໍ້ມູນສົມມຸດຕາມລາຍການ "ສິ່ງທີ່ຜູ້ສອນຕ້ອງກຽມ" ໃນ basic.md ແລະ advanced.md.

## ສ້າງໄຟລ໌ໃໝ່ຈາກໂຄດ

ເນື້ອຫາສະໄລຢູ່ໃນ `build/basic.js` ແລະ `build/advanced.js`. ແກ້ເນື້ອຫາແລ້ວສ້າງໃໝ່ດ້ວຍ:

```bash
npm install pptxgenjs react react-dom react-icons sharp jszip
NODE_PATH=./node_modules node build/build.js .
```
