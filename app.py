import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# =========================
# DATABASE
# =========================
conn = sqlite3.connect('stock.db', check_same_thread=False)
c = conn.cursor()

# =========================
# CREATE TABLES
# =========================
c.execute('''
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    name TEXT,
    category TEXT,
    stock INTEGER,
    cost REAL,
    price REAL,
    unit TEXT
)
''')

c.execute('''
CREATE TABLE IF NOT EXISTS stock_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code TEXT,
    action TEXT,
    qty INTEGER,
    note TEXT,
    created_at TEXT
)
''')

conn.commit()

# =========================
# FUNCTIONS
# =========================
def add_product(code, name, category, stock, cost, price, unit):
    try:
        c.execute('''
        INSERT INTO products
        (code, name, category, stock, cost, price, unit)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (code, name, category, stock, cost, price, unit))
        conn.commit()
        return True
    except:
        return False


def get_products():
    return pd.read_sql_query("SELECT * FROM products", conn)


def update_stock(code, qty, action, note=""):
    product = c.execute(
        "SELECT stock FROM products WHERE code=?",
        (code,)
    ).fetchone()

    if not product:
        return False

    current_stock = product[0]

    if action == "IN":
        new_stock = current_stock + qty
    else:
        new_stock = current_stock - qty

    if new_stock < 0:
        return False

    c.execute(
        "UPDATE products SET stock=? WHERE code=?",
        (new_stock, code)
    )

    c.execute('''
    INSERT INTO stock_log
    (product_code, action, qty, note, created_at)
    VALUES (?, ?, ?, ?, ?)
    ''', (
        code,
        action,
        qty,
        note,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    return True


def get_logs():
    return pd.read_sql_query(
        "SELECT * FROM stock_log ORDER BY id DESC",
        conn
    )


# =========================
# UI CONFIG
# =========================
st.set_page_config(
    page_title="FIC Stock System",
    layout="wide"
)

# =========================
# SIDEBAR
# =========================
st.sidebar.title("📦 FIC Solutions")
menu = st.sidebar.radio(
    "เมนู",
    [
        "Dashboard",
        "เพิ่มสินค้า",
        "รายการสินค้า",
        "รับสินค้าเข้า",
        "เบิกสินค้าออก",
        "ประวัติการเคลื่อนไหว"
    ]
)

# =========================
# DASHBOARD
# =========================
if menu == "Dashboard":

    st.title("📊 Dashboard")

    products_df = get_products()
    logs_df = get_logs()

    total_products = len(products_df)
    total_stock = products_df['stock'].sum() if not products_df.empty else 0
    low_stock = len(products_df[products_df['stock'] <= 10]) if not products_df.empty else 0

    col1, col2, col3 = st.columns(3)

    col1.metric("จำนวนสินค้า", total_products)
    col2.metric("สินค้าคงเหลือทั้งหมด", total_stock)
    col3.metric("สินค้าใกล้หมด", low_stock)

    st.divider()

    st.subheader("⚠️ สินค้าใกล้หมด")

    if not products_df.empty:
        low_df = products_df[products_df['stock'] <= 10]

        if low_df.empty:
            st.success("ไม่มีสินค้าใกล้หมด")
        else:
            st.dataframe(low_df, use_container_width=True)

# =========================
# ADD PRODUCT
# =========================
elif menu == "เพิ่มสินค้า":

    st.title("➕ เพิ่มสินค้า")

    with st.form("add_product"):

        code = st.text_input("รหัสสินค้า")
        name = st.text_input("ชื่อสินค้า")
        category = st.text_input("หมวดหมู่")

        col1, col2 = st.columns(2)

        with col1:
            stock = st.number_input("จำนวนเริ่มต้น", min_value=0)
            cost = st.number_input("ราคาทุน", min_value=0.0)

        with col2:
            price = st.number_input("ราคาขาย", min_value=0.0)
            unit = st.text_input("หน่วย", value="ชิ้น")

        submit = st.form_submit_button("💾 บันทึกสินค้า")

        if submit:
            ok = add_product(
                code,
                name,
                category,
                stock,
                cost,
                price,
                unit
            )

            if ok:
                st.success("เพิ่มสินค้าสำเร็จ")
            else:
                st.error("รหัสสินค้านี้มีอยู่แล้ว")

# =========================
# PRODUCT LIST
# =========================
elif menu == "รายการสินค้า":

    st.title("📦 รายการสินค้า")

    df = get_products()

    # =========================
    # SEARCH
    # =========================
    search = st.text_input("🔍 ค้นหาสินค้า")

    if search:
        df = df[
            df['name'].str.contains(search, case=False) |
            df['code'].str.contains(search, case=False)
        ]

    # =========================
    # TABLE
    # =========================
    st.dataframe(df, use_container_width=True)

    # =========================
    # EXPORT CSV
    # =========================
    csv = df.to_csv(index=False).encode('utf-8-sig')

    st.download_button(
        "📥 Export CSV",
        csv,
        file_name="products.csv",
        mime="text/csv"
    )

    st.divider()

    # =========================
    # DELETE PRODUCT
    # =========================
    st.subheader("🗑️ ลบสินค้า")

    if not df.empty:

        delete_code = st.selectbox(
            "เลือกสินค้าที่ต้องการลบ",
            df['code'].tolist()
        )

        product_data = df[df['code'] == delete_code].iloc[0]

        st.warning(
            f"สินค้า: {product_data['name']} | "
            f"คงเหลือ: {product_data['stock']}"
        )

        confirm_delete = st.checkbox(
            "ยืนยันการลบสินค้า"
        )

        if confirm_delete:

            if st.button("❌ ลบสินค้าออกจากระบบ"):

                c.execute(
                    "DELETE FROM products WHERE code=?",
                    (delete_code,)
                )

                conn.commit()

                st.success("ลบสินค้าเรียบร้อยแล้ว")

                st.rerun()

    else:
        st.info("ไม่มีสินค้าในระบบ")

# =========================
# STOCK IN
# =========================
elif menu == "รับสินค้าเข้า":

    st.title("📥 รับสินค้าเข้า")

    df = get_products()

    if df.empty:
        st.warning("ยังไม่มีสินค้า")
    else:

        product_code = st.selectbox(
            "เลือกสินค้า",
            df['code'].tolist()
        )

        qty = st.number_input(
            "จำนวน",
            min_value=1
        )

        note = st.text_input("หมายเหตุ")

        if st.button("✅ รับสินค้าเข้า"):
            ok = update_stock(product_code, qty, "IN", note)

            if ok:
                st.success("อัปเดตสต๊อกสำเร็จ")
            else:
                st.error("เกิดข้อผิดพลาด")

# =========================
# STOCK OUT
# =========================
elif menu == "เบิกสินค้าออก":

    st.title("📤 เบิกสินค้าออก")

    df = get_products()

    if df.empty:
        st.warning("ยังไม่มีสินค้า")
    else:

        product_code = st.selectbox(
            "เลือกสินค้า",
            df['code'].tolist(),
            key="out_product"
        )

        qty = st.number_input(
            "จำนวน",
            min_value=1,
            key="out_qty"
        )

        note = st.text_input(
            "หมายเหตุ",
            key="out_note"
        )

        if st.button("🚚 เบิกสินค้า"):
            ok = update_stock(product_code, qty, "OUT", note)

            if ok:
                st.success("เบิกสินค้าเรียบร้อย")
            else:
                st.error("สต๊อกไม่พอ หรือเกิดข้อผิดพลาด")

# =========================
# LOGS
# =========================
elif menu == "ประวัติการเคลื่อนไหว":

    st.title("📜 ประวัติการเคลื่อนไหว")

    logs = get_logs()

    st.dataframe(logs, use_container_width=True)

    csv = logs.to_csv(index=False).encode('utf-8-sig')

    st.download_button(
        "📥 Export Logs CSV",
        csv,
        file_name="stock_logs.csv",
        mime="text/csv"
    )
