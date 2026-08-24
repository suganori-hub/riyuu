import streamlit as st
import re
import google.generativeai as genai

# ページ設定
st.set_page_config(
    page_title="志望理由書 文章化支援アプリ",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)

# タイトル
st.title("📝 志望理由書 文章化支援アプリ")
st.write("ワークシートのステップに沿って、説得力のある志望理由書を文章化しましょう！")

# NGワードとアドバイスの定義
NG_WORDS = {
    "魅力を感じた": "「どの特色に、なぜ惹かれたのか」を具体的に書きましょう。",
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
このアプリは、配布されたワークシートのステップをシステム化したものです。
左側のメニューでステップを進めながら入力してください。
入力した文章はリアルタイムでチェックされ、改善のアドバイスが表示されます。
""")

# AI設定 (サイドバー)
st.sidebar.markdown("---")
st.sidebar.subheader("🔑 AI設定 (壁打ち機能用)")
st.sidebar.write("「AIと相談しながら決める」機能を利用するには、GeminiのAPIキーが必要です。")
api_key_input = st.sidebar.text_input("Gemini API Key", type="password", help="Google AI Studio等で取得したAPIキーを入力してください。")
if api_key_input:
    st.session_state.gemini_api_key = api_key_input

st.sidebar.caption("💡 先生へ: Streamlit Cloudの Secrets に `GEMINI_API_KEY` を登録しておくと、生徒がキーを入力しなくても最初からAI機能を使えるようになります。")

# タブでステップを管理
tab1, tab2, tab3 = st.tabs(["ステップ1: 中心文の決定", "ステップ2: 5段落の本文作成", "ステップ3: 完成原稿チェック"])

# セッション状態の初期化
if "theme" not in st.session_state:
    st.session_state.theme = ""
if "method" not in st.session_state:
    st.session_state.method = ""
if "position" not in st.session_state:
    st.session_state.position = ""
if "target" not in st.session_state:
    st.session_state.target = ""

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "こんにちは！志望理由書の「核」となる一文を一緒に決めていきましょう。まずは、今あなたが一番興味を持っている学問分野や、気になっている社会の出来事（ニュース、身近な課題など）について教えてください！"}
    ]

for i in range(1, 6):
    if f"p{i}" not in st.session_state:
        st.session_state[f"p{i}"] = ""

# APIキーの取得
api_key = st.session_state.get("gemini_api_key") or st.secrets.get("GEMINI_API_KEY")

# AI壁打ち用のシステムプロンプト
system_instruction = """あなたは高校生の志望理由書作成を支援する、優しく丁寧な進路指導アドバイザーです。
生徒の「志望理由の核（中心文）」を一緒に作るため、対話を通じて以下の4つの要素を引き出してください。

1. 【テーマ】（例: 地域コミュニティの衰退問題、スマートフォンの依存症、再生可能エネルギーの普及など、具体的に探究・研究したい内容）
2. 【視点・方法】（例: 自治体と市民の協働という視点、心理学的な実験、データ分析、アンケート調査など、どうやってそれを研究するか）
3. 【立場】（例: 地域コーディネーター、開発エンジニア、スクールカウンセラーなど、将来どんな役割で活躍したいか）
4. 【対象・課題】（例: 高齢化が進む限界集落、不登校に悩む子どもたちなど、誰のどんな課題に貢献したいか）

対話のルール：
- 一度にすべての要素を聞かないでください。生徒が答えやすいよう、まずは「今、一番関心があること」や「将来やりたいこと」などを聞き、1問ずつ対話を進めてください。
- 生徒の回答が曖昧（例：「経済について学びたい」「人の役に立ちたい」など）な場合、ワークシートの注意書き「避ける形」を意識してください。
  「魅力を感じた」「人の役に立ちたい」「多くのことを学びたい」だけで終わらせないよう、「具体的にどんな現象に興味がありますか？」「どんな人のどんな課題に？」と、優しく具体化を促してください。
- 4つの要素がある程度引き出せたと判断したら、ワークシートのテンプレートの形：
  「私は【テーマ】について、【視点・方法】から研究し、将来【立場】として、【対象・課題】に貢献したい。」
  に当てはめた「中心文」を生徒に提案してください。
- 生徒がその提案に「これでいいです」「これで決定します」と納得したら、必ず、会話の最後に**全く同じ次の形式**で、4つの要素を出力してください。これによりアプリのシステム側が値を自動的に抽出してフォームに入力します。結果以外の余計な文章はタグの後ろに付けないでください。

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

# --- タブ1: 中心文の決定 ---
with tab1:
    st.header("1. 最初に、志望理由の核を一文で決める")
    st.write("「私は何を、どう研究し、将来どう生かしたいのか」を明確にします。")
    
    # モード選択
    mode = st.radio(
        "中心文の決め方を選んでください:",
        ["自分で直接入力する", "AIと相談しながら決める（壁打ちチャット）"],
        horizontal=True,
        key="generation_mode"
    )
    
    if mode == "AIと相談しながら決める（壁打ちチャット）":
        st.subheader("💬 AI壁打ちチャット")
        st.write("AIの質問に答えていくことで、あなたの志望理由の核を引き出します。")
        
        # APIキーチェック
        if not api_key:
            st.warning("⚠️ AIチャット機能を利用するには、サイドバーでGemini APIキーを入力するか、Streamlit CloudのSecretsに 'GEMINI_API_KEY' を登録してください。")
        
        # チャットコンテナ
        chat_container = st.container()
        
        # チャット履歴の表示
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    
        # ユーザー入力
        if user_input := st.chat_input("メッセージを入力してください..."):
            # ユーザーメッセージを即座に表示・保存
            st.session_state.messages.append({"role": "user", "content": user_input})
            with chat_container:
                with st.chat_message("user"):
                    st.write(user_input)
            
            # AIの回答生成
            if api_key:
                with chat_container:
                    with st.chat_message("assistant"):
                        message_placeholder = st.empty()
                        with st.spinner("AIが考えています..."):
                            try:
                                genai.configure(api_key=api_key)
                                model = genai.GenerativeModel(
                                    model_name="gemini-1.5-flash",
                                    system_instruction=system_instruction
                                )
                                chat = model.start_chat(history=get_gemini_history())
                                response = chat.send_message(user_input)
                                ai_response = response.text
                                message_placeholder.write(ai_response)
                                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                                
                                # 結果のパース
                                result_match = re.search(r"\[RESULT\](.*?)\[/RESULT\]", ai_response, re.DOTALL)
                                if result_match:
                                    result_content = result_match.group(1)
                                    theme_m = re.search(r"THEME:\s*(.*)", result_content)
                                    method_m = re.search(r"METHOD:\s*(.*)", result_content)
                                    position_m = re.search(r"POSITION:\s*(.*)", result_content)
                                    target_m = re.search(r"TARGET:\s*(.*)", result_content)
                                    
                                    if theme_m: st.session_state.theme = theme_m.group(1).strip()
                                    if method_m: st.session_state.method = method_m.group(1).strip()
                                    if position_m: st.session_state.position = position_m.group(1).strip()
                                    if target_m: st.session_state.target = target_m.group(1).strip()
                                    
                                    st.success("🎉 AIとの会話から「中心文」の4つの要素が自動決定されました！画面を下にスクロールして確認するか、次の「ステップ2」に進んでください。")
                                    st.rerun()
                            except Exception as e:
                                error_msg = f"AIの呼び出し中にエラーが発生しました。APIキーを確認してください。詳細: {e}"
                                message_placeholder.write(error_msg)
                                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                with chat_container:
                    with st.chat_message("assistant"):
                        st.write("🔑 APIキーが設定されていません。サイドバーから設定してください。")
        
        # チャットリセットボタン
        if st.button("💬 チャットを最初からやり直す"):
            st.session_state.messages = [
                {"role": "assistant", "content": "こんにちは！志望理由書の「核」となる一文を一緒に決めていきましょう。まずは、今あなたが一番興味を持っている学問分野や、気になっている社会の出来事（ニュース、身近な課題など）について教えてください！"}
            ]
            st.session_state.theme = ""
            st.session_state.method = ""
            st.session_state.position = ""
            st.session_state.target = ""
            st.rerun()

    # 共通のプレビューおよび手動調整エリア
    st.write("---")
    st.subheader("📝 「中心文」の要素調整")
    st.write("AIとの相談結果がここに入力されます。必要に応じて自分で書き換えて調整することも可能です。")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.theme = st.text_input(
            "① 【テーマ】（例: 地域コミュニティの衰退問題）", 
            value=st.session_state.theme,
            key="theme_input"
        )
        st.session_state.method = st.text_input(
            "② 【視点・方法】（例: 自治体と市民の協働という視点）", 
            value=st.session_state.method,
            key="method_input"
        )
    with col2:
        st.session_state.position = st.text_input(
            "③ 【立場】（例: 地域コーディネーター）", 
            value=st.session_state.position,
            key="position_input"
        )
        st.session_state.target = st.text_input(
            "④ 【対象・課題】（例: 高齢化が進む限界集落の維持活性化）", 
            value=st.session_state.target,
            key="target_input"
        )

    # 中心文の結合とプレビュー
    if st.session_state.theme or st.session_state.method or st.session_state.position or st.session_state.target:
        center_sentence = f"私は**{st.session_state.theme or '（テーマ）'}**について、**{st.session_state.method or '（視点・方法）'}**から研究し、将来**{st.session_state.position or '（立場）'}**として、**{st.session_state.target or '（対象・課題）'}**に貢献したい。"
        st.info(f"**【生成された中心文】**\n\n{center_sentence}")
        
        # 避けるべき形チェック
        bad_patterns = ["魅力を感じた", "人の役に立ちたい", "多くのことを学びたい"]
        found_bad = [p for p in bad_patterns if p in (st.session_state.theme + st.session_state.method + st.session_state.position + st.session_state.target)]
        if found_bad:
            st.warning(f"⚠️ **避けるべき表現が含まれています**: {', '.join(found_bad)} だけで終わる文は避けましょう。何を・どの視点で・誰に対して・どう生かすかを具体的に書き込んでください。")

# --- タブ2: 本文の下書き (5段落) ---\nwith tab2:
    st.header("2. 本文の下書き (5段落)")
    st.write("ワークシートの構成に沿って、各段落を執筆します。右側にアドバイスが表示されます。")
    
    # 5つの段落の設定
    paragraphs_info = [
        {
            "num": 1,
            "role": "きっかけ・問題意識",
            "guide": "私が【分野】に関心を持ったのは、【経験】がきっかけである。そこから【課題】に疑問を持った。",
            "condition": "体験・授業・探究など、具体的な場面を書きましょう。「興味がある」だけで終わらせないこと。"
        },
        {
            "num": 2,
            "role": "研究したい問い",
            "guide": "大学では【テーマ】について、【方法・視点】から明らかにしたい。特に【具体的な問い】に関心がある。",
            "condition": "「学びたい」より「明らかにしたい問い」に近づけ、調査や分析の方法にも触れましょう。"
        },
        {
            "num": 3,
            "role": "その大学である理由",
            "guide": "貴学の【授業・ゼミ等】では、【できる学び】に取り組める。これは、私の【関心】を深めるうえで必要である。",
            "condition": "その大学でなければならない理由として、授業名・ゼミ・研究室・実習・地域・設備などの「固有名詞」を1つ以上入れましょう。"
        },
        {
            "num": 4,
            "role": "入学後の学び方／将来像",
            "guide": "入学後は【取り組み】に挑戦し、【力】を身につけたい。そして、将来は【立場】として【どのように働くか】できる人間になりたい。",
            "condition": "「頑張る」を具体的な行動にし、職業名だけでなくどんな姿勢や力を持つ人なりたいかを書きます。"
        },
        {
            "num": 5,
            "role": "社会貢献",
            "guide": "将来は【身につけた力】を活かして、【対象・課題】に関わる形で社会に貢献したい。",
            "condition": "「人の役に立つ」を、誰の、どんな課題に、どう関わるかに言い換えましょう。"
        }
    ]
    
    full_text_list = []
    
    for p in paragraphs_info:
        st.subheader(f"第 {p['num']} 段落: {p['role']}")
        col_input, col_adv = st.columns([2, 1])
        
        with col_input:
            st.caption(f"**【テンプレートの目安】** {p['guide']}")
            text_val = st.text_area(
                f"入力欄 (第 {p['num']} 段落)",
                value=st.session_state[f"p{p['num']}"],
                key=f"p{p['num']}_input",
                height=120
            )
            st.session_state[f"p{p['num']}"] = text_val
            full_text_list.append(text_val)
            st.caption(f"文字数: {len(text_val)}文字")
            
        with col_adv:
            st.markdown(f"📌 **強くする条件**\n{p['condition']}")
            if text_val:
                advices = analyze_text(text_val)
                if advices:
                    for adv in advices:
                        st.write(adv)
                else:
                    st.success("✅ 表現上の基本的な問題はありません！")
        st.write("---")

# --- タブ3: 完成原稿チェック ---
with tab3:
    st.header("3. 完成原稿のプレビューと自己評価チェック")
    
    # 5つの段落を結合
    compiled_text = "\n\n".join([st.session_state[f"p{i}"] for i in range(1, 6) if st.session_state[f"p{i}"]])
    
    st.subheader("📝 結合した文章")
    if compiled_text:
        st.text_area("完成原稿（コピーしてWord等に貼り付けられます）", value=compiled_text, height=300)
        st.write(f"全体の文字数: {len(compiled_text)}文字 (改行含む)")
    else:
        st.info("ステップ2で段落を入力すると、ここに結合された文章が表示されます。")
        
    st.write("---")
    st.subheader("🔍 最終チェックリスト")
    st.write("文章を提出用として読み直し、以下の観点がクリアできているかチェックしましょう。")
    
    checklist = [
        {"cat": "個別性", "item": "大学名を他大学に置き換えても不自然にならないくらい、その大学固有の理由があるか。"},
        {"cat": "個別性", "item": "授業名・ゼミ・研究室・地域などの固有名詞が、自分のテーマと結びついているか。"},
        {"cat": "研究内容", "item": "「何を学びたいか」が具体的な問いや課題として書かれているか。"},
        {"cat": "研究内容", "item": "調査・実験・データ分析・文献研究など、学び方の具体的な方向性が見えるか。"},
        {"cat": "経験", "item": "高校での経験が単なる報告で終わらず、「気づき」や「大学での研究の動機」につながっているか。"},
        {"cat": "将来像", "item": "将来像が職業名だけで終わらず、どのような姿勢・力を持つ人間になりたいかが書かれているか。"},
        {"cat": "社会貢献", "item": "「人の役に立つ」が、誰の・どのような課題に・どう関わるかに言い換えられているか。"},
        {"cat": "一貫性", "item": "きっかけ、研究テーマ、その大学である理由、将来像、社会貢献が一本の線でつながっているか。"}
    ]
    
    for i, chk in enumerate(checklist):
        col_item, col_eval = st.columns([3, 1])
        with col_item:
            st.write(f"**[{chk['cat']}]** {chk['item']}")
        with col_eval:
            st.radio(f"評価 {i}", ["未達成 (×)", "やや弱い (△)", "達成 (○)"], key=f"eval_{i}", label_visibility="collapsed")
