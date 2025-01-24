import csv

import oracledb

DatabaseError = oracledb.DatabaseError


def exec_oracle_query(host, db_name, user, passwd, sql, port=1521):
    """
    Execute an oracle query and write the results to CSV.
    """
    conn_str = make_oracle_conn_string(host, port, db_name, user, passwd)
    oracledb.init_oracle_client()
    fname = "/tmp/results.csv"
    batch_size = 200
    with oracledb.connect(conn_str) as db, open(fname, "w", newline="") as f:
        cursor = db.cursor()
        cursor.execute(sql)
        field_names = [colinfo[0] for colinfo in cursor.description]
        writer = csv.DictWriter(f, field_names)
        writer.writeheader()
        for row in fetchrows(cursor, num_rows=batch_size, row_wrapper=row2dict):
            writer.writerow(row)


def make_oracle_conn_string(host, port, db_name, user, passwd):
    """
    Create an Oracle connection string.
    """
    conn_string = "{user}/{passwd}@//{host}:{port}/{db_name}".format(
        host=host, port=port, db_name=db_name, user=user, passwd=passwd
    )
    return conn_string


def row2dict(columns, row):
    """
    Wrap a tuple row iterator as a dictionary.
    """
    d = {}
    for n, column_name in enumerate(columns):
        d[column_name] = row[n]
    return d


def fetchrows(cursor, num_rows=10, row_wrapper=None):
    """
    Fetch rows in batches of size `num_rows` and yield those.
    """
    columns = list(entry[0] for entry in cursor.description)
    while True:
        rows = cursor.fetchmany(num_rows)
        if not rows:
            break
        for row in rows:
            if row_wrapper is not None:
                row = row_wrapper(columns, row)
            yield row
