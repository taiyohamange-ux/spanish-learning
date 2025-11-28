package com.example.ai

import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.lifecycleScope
import com.google.ai.client.generativeai.GenerativeModel
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

// 辞書データの型定義
data class DictionaryEntry(val word: String, val meaning: String)

class MainActivity : ComponentActivity() {

    # ★★★ ここにAPIキーを入れてください ★★★
    private val apiKey = "AIzaSyAKlVi8wS6SqEcleH6y9lK5TOmhdj7O9KQ"

    // 辞書データを保持するリスト
    private var dictionaryList: List<DictionaryEntry> = emptyList()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // アプリ起動時に辞書を読み込む
        loadDictionary()

        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    DictionaryAppScreen()
                }
            }
        }
    }

    // 辞書読み込みロジック
    private fun loadDictionary() {
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val inputStream = assets.open("spanish_dict.json")
                val jsonString = inputStream.bufferedReader().use { it.readText() }
                val listType = object : TypeToken<List<DictionaryEntry>>() {}.type
                dictionaryList = Gson().fromJson(jsonString, listType)
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    # 辞書検索ロジック（★ここを見やすく改良しました★）
    fun searchDictionary(text: String): String {
        if (dictionaryList.isEmpty()) return "（辞書データを準備中...）"

        val words = text.lowercase().split(Regex("[^a-záéíóúñü]+"))
        val results = StringBuilder()
        val foundSet = mutableSetOf<String>()

        for (w in words) {
            if (w.length < 2 || foundSet.contains(w)) continue

            val entry = dictionaryList.find { it.word.equals(w, ignoreCase = true) }

            if (entry != null) {
                // ★意味データの中の記号を、見やすい形に変換する処理★
                var cleanMeaning = entry.meaning
                    .replace("∥", "\n      ") // 区切り文字「∥」を「改行＋インデント」に変換
                    .replace("―", "-")       // 長いダッシュ「―」をハイフン「-」に変換

                // 単語と意味を見やすく整形して追加
                results.append("・${entry.word} :\n      $cleanMeaning\n\n")
                foundSet.add(w)
            }
        }

        if (results.isEmpty()) return "（辞書に一致する単語はありませんでした）"
        return results.toString()
    }

    // AI解説ロジック
    suspend fun analyzeTextWithGemini(userText: String, dictionaryInfo: String): Pair<String, String> {
        val prompt = """
            あなたはスペイン語教育のプロフェッショナルです。
            以下の「参照辞書データ」を最優先で使用し、ユーザーのテキストを解説・翻訳してください。

            ### ユーザーの入力テキスト:
            $userText

            ### 参照すべき辞書データ (ローカル検索結果):
            $dictionaryInfo

            ### 指示
            1. 単語解説:
               - 文頭から順に単語を解説してください。
               - 辞書データにある単語は、その意味を必ず使用してください。
               - 定冠詞 (el, la, los, las) は除外してください。
            
            2. 日本語訳:
               - 文章全体の自然な日本語訳を作成してください。

            ### 重要：出力フォーマット
            解説と翻訳の間には、区切り文字として「|||」を挿入してください。
            箇条書きの頭には「・」を使用してください。
            
            (出力例)
            【単語解説】
            ・word (不定詞: ...): 意味
            ...
            |||
            【日本語訳】
            ここに翻訳文...
        """.trimIndent()

        return try {
            val generativeModel = GenerativeModel(
                modelName = "gemini-2.5-flash",
                apiKey = apiKey
            )
            val response = generativeModel.generateContent(prompt)
            val fullText = response.text ?: "回答が得られませんでした"

            // アスタリスク削除
            val cleanText = fullText.replace("**", "")

            // 区切り文字で分割
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
}

@Composable
fun DictionaryAppScreen() {
    val context = LocalContext.current

    var inputText by remember { mutableStateOf("") }
    var dictionaryResult by remember { mutableStateOf("") }
    var explanationResult by remember { mutableStateOf("") }
    var translationResult by remember { mutableStateOf("") }
    var isLoading by remember { mutableStateOf(false) }

    var selectedTabIndex by remember { mutableIntStateOf(0) }
    val tabs = listOf("単語解説", "日本語訳")

    val scope = rememberCoroutineScope()
    val activity = context as? MainActivity

    Column(
        modifier = Modifier.fillMaxSize()
    ) {
        // 上部エリア
        Column(
            modifier = Modifier.padding(16.dp)
        ) {
            OutlinedTextField(
                value = inputText,
                onValueChange = { inputText = it },
                label = { Text("スペイン語を入力") },
                modifier = Modifier.fillMaxWidth().height(100.dp)
            )

            Spacer(modifier = Modifier.height(10.dp))

            Button(
                onClick = {
                    if (inputText.isEmpty()) {
                        Toast.makeText(context, "文章を入力してください", Toast.LENGTH_SHORT).show()
                        return@Button
                    }
                    isLoading = true
                    selectedTabIndex = 0

                    scope.launch {
                        val dictInfo = activity?.searchDictionary(inputText) ?: ""
                        dictionaryResult = dictInfo

                        val (expl, trans) = activity?.analyzeTextWithGemini(inputText, dictInfo) ?: Pair("エラー", "")
                        explanationResult = expl
                        translationResult = trans

                        isLoading = false
                    }
                },
                modifier = Modifier.fillMaxWidth(),
                enabled = !isLoading
            ) {
                Text(if (isLoading) "解析中..." else "AI解説スタート")
            }
        }

        if (isLoading) {
            LinearProgressIndicator(modifier = Modifier.fillMaxWidth())
        }

        // タブ
        TabRow(selectedTabIndex = selectedTabIndex) {
            tabs.forEachIndexed { index, title ->
                Tab(
                    text = { Text(title) },
                    selected = selectedTabIndex == index,
                    onClick = { selectedTabIndex = index }
                )
            }
        }

        // 下部エリア
        Column(
            modifier = Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(16.dp)
        ) {
            if (selectedTabIndex == 0) {
                // --- タブ1：単語解説 ---
                if (dictionaryResult.isNotEmpty()) {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFE3F2FD)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("【辞書検索結果】", fontWeight = FontWeight.Bold, color = Color(0xFF1565C0))
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(text = dictionaryResult, fontSize = 16.sp)
                        }
                    }
                    Spacer(modifier = Modifier.height(16.dp))
                }

                if (explanationResult.isNotEmpty()) {
                    Text(text = explanationResult, fontSize = 16.sp)
                } else if (!isLoading && dictionaryResult.isEmpty()) {
                    Text("ここに解説が表示されます", color = Color.Gray)
                }

            } else {
                // --- タブ2：日本語訳 ---
                if (translationResult.isNotEmpty()) {
                    Card(
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFFFF3E0)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(16.dp)) {
                            Text("【翻訳】", fontWeight = FontWeight.Bold, color = Color(0xFFE65100))
                            Spacer(modifier = Modifier.height(8.dp))
                            Text(text = translationResult, fontSize = 18.sp, fontWeight = FontWeight.Medium)
                        }
                    }
                } else if (!isLoading) {
                    Text("ここに翻訳が表示されます", color = Color.Gray)
                }
            }
        }
    }

}

