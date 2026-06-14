import csv
import os

def write_row_csv(row):
    os.makedirs("output", exist_ok=True)

    output_file = "project/output/network_stats.csv"
    file_exists = os.path.isfile(output_file)

    with open(output_file, "a", newline="") as file:
        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(["mac_fill", "flood_pressure", "avg_age"])

        writer.writerow(row)