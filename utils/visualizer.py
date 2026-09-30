import os
import json
import graphviz

def draw_dag_from_json(json_path, output_dir, filename="DAG_Motivational"):
    """
    Reads the DAG from the JSON input file and generates a publication-quality
    image matching the style of the TMDS paper with enforced horizontal ordering.
    """
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    dot = graphviz.Digraph(name=filename, format='png')
    
    # تنظیمات ظاهری برای تطابق با مقالات IEEE
    dot.attr(rankdir='TB', nodesep='0.6', ranksep='0.8')
    dot.attr('node', shape='circle', fontname='serif,italic', 
             fontsize='16', fixedsize='true', width='0.6',
             color='black', fillcolor='white', style='filled')
    dot.attr('edge', fontname='serif', fontsize='14', arrowsize='0.8')

    # ۱. رسم تمام گره‌ها با برچسب‌های ریاضی (HTML-like)
    tasks = data['execution_data'].keys()
    for task in tasks:
        t_id = task.split('_')[1]
        html_label = f"<&tau;<sub>{t_id}</sub>>"
        dot.node(task, label=html_label)
        
    # ۲. لایه‌بندی هم‌سطح و اعمال اجباری ترتیب افقی با یال‌های نامرئی
    # لایه دوم: 2 تا 6
    with dot.subgraph() as s:
        s.attr(rank='same')
        layer2_nodes = [f'task_{i}' for i in range(2, 7)]
        for node in layer2_nodes:
            s.node(node)
        # اجبار به ترتیب افقی (چپ به راست) با یال نامرئی
        for i in range(len(layer2_nodes) - 1):
            s.edge(layer2_nodes[i], layer2_nodes[i+1], style='invis')
            
    # لایه سوم: 7 تا 9
    with dot.subgraph() as s:
        s.attr(rank='same')
        layer3_nodes = [f'task_{i}' for i in range(7, 10)]
        for node in layer3_nodes:
            s.node(node)
        # اجبار به ترتیب افقی (چپ به راست) با یال نامرئی
        for i in range(len(layer3_nodes) - 1):
            s.edge(layer3_nodes[i], layer3_nodes[i+1], style='invis')

    # ۳. رسم یال‌های اصلی گراف
    for edge_str, weight in data['communication'].items():
        u, v = edge_str.split('|')
        # برای جلوگیری از تداخل وزن‌ها روی یال‌های نامرئی، تنظیمات constraint اعمال می‌شود
        dot.edge(u, v, label=str(int(weight)))

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    dot.render(output_path, cleanup=True)