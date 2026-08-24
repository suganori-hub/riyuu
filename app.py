import streamlit as st
import re

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

if f"p1" not in st.session_state:
    for i in range(1, 6):
        st.session_state[f"p{i}"] = ""

# --- タブ1: 中心文の決定 ---
with tab1:
    st.header("1. 最初に、志望理由の核を一文で決める")
    st.write("「私は何を、どう研究し、将来どう生かしたいのか」を明確にします。")
    
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.theme = st.text_input("① 【テーマ】（例: 地域コミュニティの衰退問題）", value=st.session_state.theme)
        st.session_state.method = st.text_input("② 【視点・方法】（例: 自治体と市民の協働という視点）", value=st.session_state.method)
    with col2:
        st.session_state.position = st.text_input("③ 【立場】（例: 地域コーディネーター）", value=st.session_state.position)
        st.session_state.target = st.text_input("④ 【対象・課題】（例: 高齢化が進む限界集落の維持活性化）", value=st.session_state.target)
        
    # 中心文の結合
    if st.session_state.theme or st.session_state.method or st.session_state.position or st.session_state.target:
        center_sentence = f"私は**{st.session_state.theme or '（テーマ）'}**について、**{st.session_state.method or '（視点・方法）'}**から研究し、将来**{st.session_state.position or '（立場）'}**として、**{st.session_state.target or '（対象・課題）'}**に貢献したい。"
        st.info(f"**生成された中心文:**\n\n{center_sentence}")
        
        # 避けるべき形チェック
        bad_patterns = ["魅力を感じた", "人の役に立ちたい", "多くのことを学びたい"]
        found_bad = [p for p in bad_patterns if p in (st.session_state.theme + st.session_state.method + st.session_state.position + st.session_state.target)]
        if found_bad:
            st.warning(f"⚠️ **避けるべき表現が含まれています**: {', '.join(found_bad)} だけで終わる文は避けましょう。何を・どの視点で・誰に対して・どう生かすかを具体的に書き込んでください。")

# --- タブ2: 本文の下書き (5段落) ---
with tab2:
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
            "condition": "「頑張る」を具体的な行動にし、職業名だけでなくどんな姿勢や力を持つ人になりたいかを書きます。"
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
