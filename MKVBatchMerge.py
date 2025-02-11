import os
import subprocess

BASE_FOLDER = os.path.dirname(os.path.abspath(__file__))

def get_folder(prompt, default_folder, create_if_missing=False):
    while True:
        user_input = input(f"{prompt} (default: {default_folder}): ").strip()
        if user_input:
            if not os.path.exists(user_input):
                if create_if_missing:
                    os.makedirs(user_input, exist_ok=True)
                    print(f"Created folder: {user_input}")
                    return user_input
                else:
                    print(f"Error: The specified folder '{user_input}' does not exist. Try again.")
            else:
                return user_input
        else:
            return default_folder

print("MKV Attachment Script")
print("\n####################################################################################################\n")
print("\033[31m This script requires ffmpeg and mkvtoolnix to be installed (& added to the windows path variables)!\033[0m")
print("\n####################################################################################################\n")
print("This script can be used to batch process mkv files allowing to easily add intro and outro sequences.\nChapters will be created based on the attached files with the corresponding names.\n")
print("Folder structure reuirements (custom or provided folders can be used):")
print(" - 'Input':         MKV files to be processed.")
print(" - 'Attachments':   MKV files that should be attached to the files inside the Input folder.")
print(" - 'Output':        Processed MKV Files.")

print("\n####################################################################################################\n")

INPUT_FOLDER = get_folder("Enter a custom input folder path", os.path.join(BASE_FOLDER, "Input"))
ATTACHMENTS_FOLDER = get_folder("Enter a custom attachment folder path", os.path.join(BASE_FOLDER, "Attachments"))
OUTPUT_FOLDER = get_folder("Enter a custom output folder path", os.path.join(BASE_FOLDER, "Output"), create_if_missing=True)
os.makedirs(ATTACHMENTS_FOLDER, exist_ok=True)

def list_attachments():
    files = sorted(os.listdir(ATTACHMENTS_FOLDER))
    print("Available files:")
    print("[0] Episode")
    for i, file in enumerate(files, start=1):
        print(f"[{i}] {file}")
    return files

def format_duration(seconds):
    h, remainder = divmod(seconds, 3600)
    m, s = divmod(remainder, 60)
    return f"{int(h):02}:{int(m):02}:{int(s):02}.{int((s % 1) * 1000):03}"

def get_duration(file_path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return float(result.stdout.strip())

def create_chapters(output_path, sequence, episode_file, custom_chapter_name=None):
    chapter_file = os.path.splitext(output_path)[0] + ".txt"
    current_time = 0.0
    episode_filename = os.path.splitext(os.path.basename(episode_file))[0]  # Use episode filename for chapter name
    with open(chapter_file, "w") as f:
        for i, file in enumerate(sequence):
            duration = get_duration(file)
            f.write(f"CHAPTER{i+1:02}={format_duration(current_time)}\n")
            if file == episode_file:
                # Use user-provided custom chapter name or episode filename if none provided
                chapter_name = custom_chapter_name if custom_chapter_name else episode_filename
                f.write(f"CHAPTER{i+1:02}NAME={chapter_name}\n")
            else:
                chapter_name = os.path.splitext(os.path.basename(file))[0]
                f.write(f"CHAPTER{i+1:02}NAME={chapter_name}\n")
            current_time += duration

    temp_output = os.path.splitext(output_path)[0] + "_temp.mkv"
    subprocess.run(
        ["mkvmerge", "-o", temp_output, "--chapters", chapter_file, output_path],
        check=True
    )
    os.remove(chapter_file)
    if os.path.exists(output_path):
        os.remove(output_path)
    os.replace(temp_output, output_path)

def concatenate_files(output_path, sequence):
    concat_list_path = os.path.join(OUTPUT_FOLDER, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for file in sequence:
            f.write(f"file '{os.path.abspath(file)}'\n")
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list_path, "-c", "copy", output_path],
        check=True
    )
    os.remove(concat_list_path)

def process_episodes(selected_indices, attachments_files, custom_episode_chapter_name):
    episodes = [file for file in sorted(os.listdir(INPUT_FOLDER)) if file.endswith(".mkv")]
    for episode in episodes:
        episode_file = os.path.join(INPUT_FOLDER, episode)
        sequence = [attachments_files[i - 1] if i > 0 else episode_file for i in selected_indices]
        output_path = os.path.join(OUTPUT_FOLDER, episode)

        print(f"Processing: {episode}")
        temp_output_path = os.path.splitext(output_path)[0] + "_temp_concat.mkv"
        concatenate_files(temp_output_path, sequence)

        # Overwrite output file if it exists
        if os.path.exists(output_path):
            os.remove(output_path)
        os.rename(temp_output_path, output_path)

        create_chapters(output_path, sequence, episode_file, custom_episode_chapter_name)

def main():
    attachments_files = [os.path.join(ATTACHMENTS_FOLDER, file) for file in list_attachments()]
    
    # First ask user for the clips to attach
    try:
        user_input = input("Enter the indices of the files to be added (comma-separated): ").strip()
        selected_indices = [int(x) for x in user_input.split(",")]
        if 0 not in selected_indices:
            raise ValueError("You must include the episode index (index 0).")
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to close...")
        return

    # Then ask for custom episode chapter name
    custom_episode_chapter_name = input("Enter a custom chapter name to be used for all episodes (press Enter to use the filename): ").strip()
    if not custom_episode_chapter_name:
        custom_episode_chapter_name = None  # Use filename as default if no input

    try:
        process_episodes(selected_indices, attachments_files, custom_episode_chapter_name)
        print("All files processed successfully!")
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to close...")
        return

    input("Press Enter to close...")

if __name__ == "__main__":
    main()
