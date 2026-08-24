import streamlit as st
import re
import google.generativeai as genai

# ページ設定
st.set_page_config(
    page_title="国公立推薦特化型 志望理由書文章化支援アプリ",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# タイトル
st.title("📝 国公立推薦特化型 志望理由書文章化支援アプリ")
st.markdown("---")

# NGワードとアドバイスの定義
NG_WORDS = {
    "魅力を感じた": "「どの特色に、なぜ惹かれたのか」を自分の言葉で具体的に書きましょう。",
    "教育方針に共感した": "「どの教育方針に、自分のどのような経験や姿勢が合致しているか」を具体的に書きましょう。",
    "さまざまなこと": "「さまざまな」という言葉を避け、具体的に「何を学ぶか」を書きましょう。",
    "多くのこと": "具体的に「何について学ぶか」を書きましょう。",
    "人の役に立ちたい": "「誰の、どのような課題に、どう関わりたいか」と言い換えましょう。",
    "社会に貢献したい": "「どのような課題に関わる形で、どう社会に貢献したいか」を具体的に書きましょう。",
    "将来に生かしたい": "具体的に「どのような場面で、どう生かすか」を書きましょう。",
    "視野を広げる": "視野を広げた結果、「何を成し遂げたいか」を書きましょう。",
    "深く学びたい": "「深く」ではなく、具体的に「どのような方法（調査・実験など）で学ぶか」を書きましょう。"
}

# 共通の解析・アドバイス関数
def analyze_text(text):
    warnings = []
    # 1. NGワードチェック
    for word, advice in NG_WORDS.items():
        if word in text:
            warnings.append(f"⚠️ **「{word}」が含まれています**: {advice}")
    
    # 2. 一文の長さチェック (句点「。」で分割)
    sentences = re.split(r'[。！？]', text)
    for s in sentences:
        s = s.strip()
        if len(s) > 60:
            warnings.append(f"⚠️ **一文が長すぎます ({len(s)}文字)**: 「{s[:15]}...」の文は60文字を超えています。二文に分けられないか確認しましょう。")
            
    return warnings

# サイドバー
st.sidebar.header("💡 アプリの使い方")
st.sidebar.write("""
このアプリは、国公立大学の推薦・総合型選抜に対応した志望理由書作成ワークシートをシステム化したものです。
コピペを使って段階的（3ステップ）に進めることで、大学に「ここで学ぶ必然性」が伝わる強力な文章を練り上げます。
""")

# AI設定 (サイドバー)
st.sidebar.markdown("---")
st.sidebar.subheader("🔑 AI設定 (壁打ち・添削用)")
st.sidebar.write("「AI壁打ち」および「AI厳格添削」機能を利用するには、GeminiのAPIキーが必要です。")
api_key_input = st.sidebar.text_input("Gemini API Key", type="password", help="Google AI Studio等で取得したAPIキーを入力してください。")
if api_key_input:
    st.session_state.gemini_api_key = api_key_input

st.sidebar.caption("💡 先生へ: Streamlit Cloudの Secrets に `GEMINI_API_KEY` を登録しておくと、生徒がキーを入力しなくても最初からすべてのAI機能を使えるようになります。")

# APIキーの取得
api_key = st.session_state.get("gemini_api_key") or st.secrets.get("GEMINI_API_KEY")

# セッション状態の初期化
if "theme" not in st.session_state:
    st.session_state.theme = ""
if "method" not in st.session_state:
    st.session_state.method = ""
if "position" not in st.session_state:
    st.session_state.position = ""
if "target" not in st.session_state:
    st.session_state.target = ""

if "step1_sentence" not in st.session_state:
    st.session_state.step1_sentence = ""

if "step2_p1" not in st.session_state: st.session_state.step2_p1 = ""
if "step2_p2" not in st.session_state: st.session_state.step2_p2 = ""
if "step2_p3" not in st.session_state: st.session_state.step2_p3 = ""
if "step2_p4" not in st.session_state: st.session_state.step2_p4 = ""
if "step2_p5" not in st.session_state: st.session_state.step2_p5 = ""

if "step2_compiled" not in st.session_state:
    st.session_state.step2_compiled = ""

if "step3_input" not in st.session_state:
    st.session_state.step3_input = ""

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "こんにちは！国公立大学の推薦合格を目指して、志望理由書の「核（中心文）」を一緒に固めていきましょう！\n\nまずは、あなたが今高校での探究活動や日常生活の中で、もっとも「疑問に思っていること」や「解決したい地域・社会の課題」について、短くても良いので教えてください！"}
    ]

# AI壁打ち用のシステムプロンプト (国公立推薦特化)
system_instruction_step1 = """あなたは国公立大学の学校推薦型選抜・総合型選抜を志望する高校生の指導を行う、極めて優秀で熱意ある進路指導アドバイザーです。
生徒の「志望理由の核（中心文）」を妥協なく、かつ温かく一緒に作るため、対話を通じて以下の4つの要素を引き出してください。

1. 【テーマ】（例: 地域コミュニティの衰退問題、再生可能エネルギーの普及、不登校問題など、具体的に探究・研究したい内容）
2. 【視点・方法】（例: 自治体と市民の協働という視点、心理学的な実験、データ分析、アンケート調査、文献研究など、どうやってそれを研究するか）
3. 【立場】（例: 地域コーディネーター、開発エンジニア、臨床心理士など、将来どんな役割で活躍したいか）
4. 【対象・課題】（例: 高齢化が進む限界集落、心の病を抱える子どもたちなど、誰のどんな課題に貢献したいか）

対話のルール：
- 一度にすべての要素を聞かないでください。生徒が答えやすいよう、まずは「今、一番関心があること」や「将来やりたいこと」などを聞き、1問ずつ丁寧に対話を進めてください。
- 生徒の回答が曖昧（例：「経済を学びたい」「人の役に立ちたい」など）な場合、絶対にそのまま認めず、「具体的にどんな現象に興味がありますか？」「どんな人のどんな課題に？」と、優しく掘り下げてください。
- 特に「アドミッション・ポリシー（AP）に共感した」や「貴学に魅力を感じた」という丸写しの言葉は却下し、「どの特色に、なぜ惹かれたのか」を言葉にさせてください。
- 4つの要素が引き出せたら、以下のテンプレートに当てはめた「中心文」を提案してください：
  「私は【テーマ】について、【視点・方法】から研究し、将来【立場】として、【対象・課題】に貢献したい。」
- 生徒がその提案に納得したら、必ず、会話の最後に以下の形式で4つの要素を出力してください。結果以外の余計な文章はタグの後ろに絶対に付けないでください。

[RESULT]
THEME: {抽出したテーマ}
METHOD: {抽出した視点・方法}
POSITION: {抽出した立場}
TARGET: {抽出した対象・課題}
[/RESULT]
"""

# Gemini 履歴変換用関数
def get_gemini_history():
    history = []
    for msg in st.session_state.messages[1:]:
        role = "user" if msg["role"] == "user" else "model"
        history.append({
            "role": role,
            "parts": [msg["content"]]
        })
    return history

# --- タブによる3ステップ構成 ---
tab1, tab2, tab3 = st.tabs([
    "📍 ステップ①：志望理由の核を決める（AI壁打ち）", 
    "✍️ ステップ②：5つの段落に肉付けする（下書き）", 
    "🔍 ステップ③：国公立推薦 最終関門チェック（推敲）"
])

# ==========================================
# --- タブ1: ステップ①：中心文の決定 ---
# ==========================================
with tab1:
    st.header("📍 ステップ①：志望理由の核を一文で決める")
    st.write("「私は何を、どう研究し、将来どう生かしたいのか」の軸（中心文）をAIとの壁打ち対話で決定します。")
    
    col_chat, col_preview = st.columns([3, 2])
    
    with col_chat:
        st.subheader("💬 AI壁打ちチャット")
        
        # APIキーチェック
        if not api_key:
            st.warning("⚠️ AIチャット機能を利用するには、サイドバーでGemini APIキーを入力するか、Streamlit CloudのSecretsに 'GEMINI_API_KEY' を登録してください。")
        
        # チャットコンテナ
        chat_container = st.container(height=400)
        
        # チャット履歴の表示
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    
        # ユーザー入力
        if user_input := st.chat_input("AIに相談する..."):
            st.session_state.messages.append({"role": "user", "content": user_input})
            with chat_container:
                with st.chat_message("user"):
                    st.write(user_input)
            
            # AIの回答生成
            if api_key:
                with chat_container:
                    with st.chat_message("assistant"):
                        message_placeholder = st.empty()
                        with st.spinner("AIがあなたの考えを整理中..."):
                            try:
                                genai.configure(api_key=api_key)
                                model = genai.GenerativeModel(
                                    model_name="gemini-1.5-flash",
                                    system_instruction=system_instruction_step1
                                )
                                chat = model.start_chat(history=get_gemini_history())
                                response = chat.send_message(user_input)
                                ai_response = response.text
                                message_placeholder.write(ai_response)
                                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                                
                                # 結果の自動抽出
                                result_match = re.search(r"\\[RESULT\\](.*?)\\[/RESULT\\]", ai_response, re.DOTALL)
                                if result_match:
                                    result_content = result_match.group(1)
                                    theme_m = re.search(r"THEME:\s*(.*)", result_content)
                                    method_m = re.search(r"METHOD:\s*(.*)", result_content)
                                    position_m = re.search(r"POSITION:\s*(.*)", result_content)
                                    target_m = re.search(r"TARGET:\\s*(.*)", result_content)
                                    
                                    if theme_m: st.session_state.theme = theme_m.group(1).strip()
                                    if method_m: st.session_state.method = method_m.group(1).strip()
                                    if position_m: st.session_state.position = position_m.group(1).strip()
                                    if target_m: st.session_state.target = target_m.group(1).strip()
                                    
                                    # 中心文を組み立て
                                    st.session_state.step1_sentence = f"私は{st.session_state.theme}について、{st.session_state.method}から研究し、将来{st.session_state.position}として、{st.session_state.target}に貢献したい。"
                                    st.success("🎉 AIとの対話から「中心文」が自動作成されました！右側の調整エリアを確認してコピーしてください。")
                                    st.rerun()
                            except Exception as e:
                                error_msg = f"AIの呼び出し中にエラーが発生しました。詳細: {e}"
                                message_placeholder.write(error_msg)
                                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                with chat_container:
                    with st.chat_message("assistant"):
                        st.write("🔑 APIキーを設定すると、AIが壁打ちを開始します。")
        
        if st.button("💬 チャットをリセットして最初から相談する"):
            st.session_state.messages = [
                {"role": "assistant", "content": "こんにちは！国公立大学の推薦合格を目指して、志望理由書の「核（中心文）」を一緒に固めていきましょう！\n\nまずは、あなたが今高校での探究活動や日常生活の中で、もっとも「疑問に思っていること」や「解決したい地域・社会の課題」について、短くても良いので教えてください！"}
            ]
            st.session_state.theme = ""
            st.session_state.method = ""
            st.session_state.position = ""
            st.session_state.target = ""
            st.session_state.step1_sentence = ""
            st.rerun()

    with col_preview:
        st.subheader("📝 「中心文」の調整と確認")
        st.write("AIとの相談で決まった各要素がここに入ります。直接手動で修正も可能です。")
        
        st.session_state.theme = st.text_input("① 【テーマ】（研究したい具体的な内容）", value=st.session_state.theme)
        st.session_state.method = st.text_input("② 【視点・方法】（どのようなアプローチで研究するか）", value=st.session_state.method)
        st.session_state.position = st.text_input("③ 【立場】（将来活躍したい具体的な職業・役割）", value=st.session_state.position)
        st.session_state.target = st.text_input("④ 【対象・課題】（誰の、どんな課題に貢献したいか）", value=st.session_state.target)
        
        # 手動組み立て
        if st.session_state.theme or st.session_state.method or st.session_state.position or st.session_state.target:
            st.session_state.step1_sentence = f"私は{st.session_state.theme or '（テーマ）'}について、{st.session_state.method or '（視点・方法）'}から研究し、将来{st.session_state.position or '（立場）'}として、{st.session_state.target or '（対象・課題）'}に貢献したい。"
        
        st.markdown("---")
        st.write("👉 **これをコピーして【ステップ②】の「中心文ペースト欄」に貼り付けましょう！**")
        st.text_area("完成した中心文 (一文)", value=st.session_state.step1_sentence, height=80, key="step1_sentence_area")

# ==========================================
# --- タブ2: ステップ②：5つの段落への肉付け ---
# ==========================================
with tab2:
    st.header("✍️ ステップ②：5つの段落に肉付けする")
    st.write("ステップ①で決めた「軸（中心文）」を見つめながら、文章全体の構成を具体的に肉付けしていきます。")
    
    # コピペエリア
    st.subheader("🎯 ガイドライン（ステップ①からコピペ）")
    pasted_center = st.text_area(
        "ステップ①で決定した「中心文」をここに貼り付けてください（常に意識しながら書き進めるため）",
        placeholder="例: 私は地域コミュニティの衰退問題について、自治体と市民の協働という視点から研究し、将来地域コーディネーターとして、高齢化が進む限界集落の維持活性化に貢献したい。",
        height=70
    )
    
    st.markdown("---")
    st.subheader("🧱 5段落構成の下書き作成")
    
    # 5つの段落設定
    paragraphs_info = [
        {
            "key": "step2_p1",
            "role": "第1段落：きっかけ・問題意識",
            "guide": "【テンプレート】私が【分野】に関心を持ったのは、【経験】がきっかけである。そこから【課題】に疑問を持った。",
            "condition": "💡 **国公立推薦を強くする条件**:\n\n高校での具体的な体験、授業、探究活動などの場面をしっかり書きましょう。単に「興味がある」という主観的な報告で終わらせないことが極めて重要です。"
        },
        {
            "key": "step2_p2",
            "role": "第2段落：研究したい問い",
            "guide": "【テンプレート】大学では【テーマ】について、【方法・視点】から明らかにしたい。特に【具体的な問い】に関心がある。",
            "condition": "💡 **国公立推薦を強くする条件**:\n\n単なる「受動的な勉強（学びたい）」ではなく、自ら「明らかにしたい問い（研究テーマ）」を問いかけ、調査・実験・データ分析などの方向性を示しましょう。"
        },
        {
            "key": "step2_p3",
            "role": "第3段落：その大学である理由（最重要）",
            "guide": "【テンプレート】貴学の【授業・ゼミ等】では、【できる学び】に取り組める。これは、私の【関心】を深めるうえで必要である。",
            "condition": "💡 **国公立推薦を強くする条件**:\n\n他大学の同種学部ではなく「なぜその国公立大学なのか」を説明します。大学固有の授業名、ゼミ、研究室、地域プログラムなどの**固有名詞を必ず1つ以上**入れ、研究テーマと結びつけましょう。"
        },
        {
            "key": "step2_p4",
            "role": "第4段落：入学後の学び方／将来像",
            "guide": "【テンプレート】入学後は【取り組み】に挑戦し、【力】を身につけたい。そして、将来は【立場】として【どのように働くか】できる人間になりたい。",
            "condition": "💡 **国公立推薦を強くする条件**:\n\n「大学生活を頑張りたい」といった抽象表現は避け、具体的な行動計画（実習、資格、留学など）を記述します。また、職業名だけでなく「どのような姿勢や力を持つ人間になりたいか」を明確にします。"
        },
        {
            "key": "step2_p5",
            "role": "第5段落：社会貢献",
            "guide": "【テンプレート】将来は【身につけた力】を活かして、【対象・課題】に関わる形で社会に貢献したい。",
            "condition": "💡 **国公立推薦を強くする条件**:\n\n「人の役に立つ」という曖昧な表現を完全に排除します。「誰の」「どのような課題に」「どう関わるか」を言葉にして、社会における自分の役割を示します。"
        }
    ]
    
    # 5段落の入力フォーム
    p_texts = []
    for p in paragraphs_info:
        st.subheader(p["role"])
        col_inp, col_cnd = st.columns([3, 2])
        
        with col_inp:
            st.caption(p["guide"])
            p_val = st.text_area(
                "下書き入力エリア",
                value=st.session_state[p["key"]],
                key=f"{p['key']}_input",
                height=150,
                label_visibility="collapsed"
            )
            st.session_state[p["key"]] = p_val
            p_texts.append(p_val)
            st.caption(f"文字数: {len(p_val)} 文字")
            
            # 各段落ごとのローカルリアルタイムルールチェック
            if p_val:
                warnings = analyze_text(p_val)
                for w in warnings:
                    st.write(w)
                    
        with col_cnd:
            st.info(p["condition"])
        st.markdown("---")
        
    # 5段落の結合プレビュー
    st.subheader("📝 5段落を統合した完成原稿案")
    compiled_draft = "\n\n".join([st.session_state[f"step2_p{i}"] for i in range(1, 6) if st.session_state[f"step2_p{i}"]])
    st.session_state.step2_compiled = compiled_draft
    
    st.write("👉 **これをコピーして【ステップ③】の「最終添削ペースト欄」に貼り付けましょう！**")
    st.text_area(
        "統合された下書きテキスト",
        value=st.session_state.step2_compiled,
        height=250,
        key="step2_compiled_area"
    )
    if compiled_draft:
        st.caption(f"全体の文字数: {len(compiled_draft)} 文字 (改行を含む)")

# ==========================================
# --- タブ3: ステップ③：国公立推薦 最終関門チェック ---
# ==========================================
with tab3:
    st.header("🔍 ステップ③：国公立推薦 最終関門チェック（推敲）")
    st.write("ステップ②で肉付けした下書きをコピペし、国公立大学の推薦指導基準に基づく「厳しいAIチェック」と「詳細な自己診断」を行います。")
    
    # 下書きコピペエリア
    st.subheader("📥 最終添削ペースト欄（ステップ②からコピペ）")
    step3_input_text = st.text_area(
        "ステップ②で統合した文章、または現在の志望理由書をここに貼り付けてください：",
        value=st.session_state.step3_input,
        placeholder="ここに文章を貼り付けると、下に自動でエラーチェックとチェックリストが表示されます。",
        height=250,
        key="step3_input_area"
    )
    st.session_state.step3_input = step3_input_text
    
    if step3_input_text:
        st.caption(f"現在の入力文字数: {len(step3_input_text)} 文字")
        
        # 1. プログラムによる基本ルール自動検知
        st.subheader("🚨 基本ルール違反検知（リアルタイム）")
        failures = analyze_text(step3_input_text)
        if failures:
            for f_msg in failures:
                st.markdown(f_msg)
        else:
            st.success("✅ 抽象表現の不使用、一文60文字制限など、基本表記ルールをすべてクリアしています！")
            
        st.markdown("---")
        
        # 2. AIによる国公立推薦 厳格添削
        st.subheader("🤖 AI国公立推薦 厳格添削フィードバック")
        st.write("国公立推薦で勝負できる文章か、大学の求めるAP（求める人物像）や他大学との差別化ができているかをAIが徹底分析します。")
        
        if not api_key:
            st.warning("🔑 AI厳格添削を利用するには、サイドバーでGemini APIキーを設定してください。")
        else:
            if st.button("🔥 AIによる『国公立推薦 厳格添削』を実行する"):
                with st.spinner("推薦指導アドバイザーが文章を厳しく添削中..."):
                    try:
                        genai.configure(api_key=api_key)
                        model = genai.GenerativeModel("gemini-1.5-flash")
                        
                        system_instruction_step3 = """あなたは国公立大学の学校推薦型選抜や総合型選抜の指導で、毎年数多くの合格者を輩出している超一流の進路指導教諭です。
生徒が書いた志望理由書の全文を読み、以下の厳しい国公立推薦指導の観点（特にアドミッション・ポリシーへの合致や、他大学でなく『その大学で学ぶ必然性』）から評価し、具体的な赤ペン添削と改善アクションを提示してください。

【評価の極意（添削基準）】：
1. AP（アドミッションポリシー）の丸写しがないか：「APに共感した」「求める人物像に合致している」といった手抜きの表現は絶対に不合格になります。生徒自身の経験と言葉でそれが示せているか。
2. その大学である理由の「必然性」：大学名だけを他大学（私立や別の国公立）に置き換えても意味が通じる場合は、容赦なく「具体性不足」と指摘してください。授業名、ゼミ、研究室、地域連携プロジェクト等の固有名詞が、本人の研究テーマと本当に結びついているか。
3. 受動的な「勉強したい」になっていないか：大学を単なる「教えてもらう塾」と考えている甘い姿勢がないか。自ら「問い」を立てて主体的に研究・調査する姿勢があるか。
4. 表現の厳格さ：「魅力を感じた」「さまざまな」といった具体性のない言葉や、一文が長すぎて何を言いたいか分からない箇所（60文字超）がないか。

【出力フォーマット】：
## 🌟 国公立推薦・総合型選抜 総合評価
[A（このまま出願可能） / B（あと一歩の修正が必要） / C（大幅な見直しが必要）]

## 🔴 厳しい指摘（ここが国公立推薦の合格基準に達していません！）
- （1つ〜3つ、具体的にどの文章がどう甘いかを厳しく、しかし熱意を持って指摘してください）

## ✏️ 劇的に強くなる！赤ペン添削・書き換え具体案
- 【現状の文】:「...」
- 【改善案】:「...」
- 【解説】: なぜこのように書き換えるべきか、生徒の経験や固有名詞をどう引き出すかのヒント。

## 💡 次のステップへのアドバイス
- 生徒が明日からすぐに書き直せるような温かい激励メッセージ。
"""
                        response = model.generate_content(
                            f"【生徒の志望理由書】:\n{step3_input_text}\n\n上記を添削してください。",
                            generation_config={"system_instruction": system_instruction_step3}
                        )
                        st.markdown(response.text)
                    except Exception as e:
                        st.error(f"AI添削中にエラーが発生しました。詳細: {e}")
                        
        st.markdown("---")
        
        # 3. デジタル自己評価・相互評価チェックリスト (ワークシートの3セクション目を再現)
        st.subheader("📋 志望理由書 完成原稿チェックリスト")
        st.write("できている＝○（達成）、弱い＝△（やや弱い）、直す＝×（未達成）でチェック。△・×の項目は手動で文章をブラッシュアップしましょう。")
        
        checklist_items = [
            {"cat": "個別性", "item": "大学名を他大学に置き換えても不自然にならないくらい、その大学固有の理由がある。"},
            {"cat": "個別性", "item": "授業名・ゼミ・研究室・実習・フィールド・地域・設備などの固有名詞を、ただ挙げるだけでなく自分のテーマと結びつけている。"},
            {"cat": "研究内容", "item": "「何を学びたいか」が、学問名だけでなく具体的な問い・課題として書かれている。"},
            {"cat": "研究内容", "item": "研究したい内容について、調査・実験・比較・データ分析・フィールドワーク・文献研究など、学び方の方向が見える。"},
            {"cat": "経験", "item": "高校での経験は活動報告で終わらず、「そこから何に気づいたか」「なぜ大学で深めたいか」につながっている。"},
            {"cat": "経験", "item": "「昔から好きだった」「興味がある」だけでなく、関心が深まった具体的な場面がある。"},
            {"cat": "将来像", "item": "将来像が職業名だけで終わらず、どのような姿勢や力を持つ人間になりたいかが書かれている。"},
            {"cat": "社会貢献", "item": "「人の役に立つ」「社会に貢献する」を、誰の・どのような課題に・どう関わるかに言い換えられている。"},
            {"cat": "一貫性", "item": "きっかけ、研究したいこと、その大学である理由、将来像、社会貢献が一本の線でつながっている。"},
            {"cat": "AP", "item": "APの文言を写したり、「APに共感した」と書いたりせず、求める学生像に合う自分の経験・姿勢で示している。"},
            {"cat": "表現", "item": "大学紹介やパンフレットの要約が長くなりすぎず、主語が自分になっている。"},
            {"cat": "表現", "item": "「魅力を感じた」「さまざまな」「多くのこと」「視野を広げる」などの抽象表現を、具体的な内容に直している。"},
            {"cat": "表現", "item": "一文が長すぎない。目安として一文60字を超える文は、二文に分けられないか確認している。"}
        ]
        
        for idx, item in enumerate(checklist_items):
            col_lbl, col_rad = st.columns([4, 2])
            with col_lbl:
                st.write(f"**[{item['cat']}]** {item['item']}")
            with col_rad:
                st.radio(
                    f"評価_{idx}",
                    ["未達成 (×)", "やや弱い (△)", "達成 (○)"],
                    key=f"final_eval_{idx}",
                    horizontal=True,
                    label_visibility="collapsed"
                )
    else:
        st.info("ステップ②で作成した「統合された下書きテキスト」をコピーし、上の入力欄に貼り付けると、AI厳密添削やチェックリスト機能が起動します。")
