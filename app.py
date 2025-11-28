// AI解説ロジック（フォーマット・翻訳精度 改善版）
    suspend fun analyzeTextWithGemini(userText: String, dictionaryInfo: String): Pair<String, String> {
        val prompt = """
            あなたはスペイン語教育のプロフェッショナルです。
            以下の「参照辞書データ」とユーザーのテキストを基に、解説と翻訳を行ってください。

            ### ユーザーの入力テキスト:
            $userText

            ### 参照すべき辞書データ:
            $dictionaryInfo

            ### 指示
            1. 単語解説:
               - 文頭から順に重要な単語を解説してください。
               - **各単語は必ず「改行」して、縦にリスト表示してください。**
               - 辞書データは参考にしますが、**文脈に合わない場合（特に前置詞 de, a, y などが「文字」や「記号」として定義されている場合）は、辞書の定義を無視して、文脈に即した正しい文法説明をしてください。**
               - 熟語（例: llevar a cabo）は分解せず、熟語として解説してください。
               - 定冠詞 (el, la, los, las) は解説リストに**含めないで（完全に無視して）**ください。
            
            2. 日本語訳:
               - 辞書の定義を直訳せず、文脈を理解した自然な日本語に翻訳してください。
               - 「de」を「文字D」としたり、「la」を「ラ」と残すような誤訳は避けてください。

            ### 重要：出力フォーマット
            解説と翻訳の間には、区切り文字として「|||」を挿入してください。
            
            (出力例)
            【単語解説】
            ・word : 意味
            ・word : 意味
            ・word : 意味
            ...
            |||
            【日本語訳】
            ここに自然な翻訳文...
        """.trimIndent()

        return try {
            val generativeModel = GenerativeModel(
                modelName = "gemini-1.5-flash", 
                apiKey = apiKey
            )
            val response = generativeModel.generateContent(prompt)
            val fullText = response.text ?: "回答が得られませんでした"
            
            // 念のため、AIが改行を忘れた場合でも強制的に改行させる処理
            val cleanText = fullText
                .replace("**", "")
                .replace("* ", "・")
                .replace("- ", "・")
                // 「・」の直前が改行でない場合、改行を入れる
                .replace(Regex("([^\\n])・"), "$1\n・")

            val parts = cleanText.split("|||")
            if (parts.size >= 2) {
                Pair(parts[0].trim(), parts[1].trim())
            } else {
                Pair(cleanText, "（翻訳データがうまく分割できませんでした）")
            }
        } catch (e: Exception) {
            Pair("通信エラー: ${e.localizedMessage}", "")
        }
    }
