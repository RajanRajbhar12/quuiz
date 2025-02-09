from flask import Flask, render_template, request, jsonify
import cohere
import random

app = Flask(__name__)

co = cohere.Client(os.getenv('COHERE_API_KEY')) 

def generate_questions_from_text(input_text, question_type, num_questions):
    try:
        if question_type == 'multiple-choice':
            prompt = f"""Generate exactly {num_questions} multiple choice questions based on this text: "{input_text}"

            Rules:
            1. Generate EXACTLY {num_questions} questions
            2. Each question MUST have exactly 4 options
            3. First option must be the correct answer
            4. Follow this EXACT format for each question:

            Q: [Question text]
            1: [Correct answer]
            2: [Wrong answer]
            3: [Wrong answer]
            4: [Wrong answer]"""

        print(f"Requesting {num_questions} questions from Cohere...")

        response = co.generate(
            model='command-xlarge-nightly',
            prompt=prompt,
            max_tokens=2000,
            temperature=0.7,
            num_generations=1
        )

        generated_text = response.generations[0].text.strip()

        # Initialize variables
        questions = []
        current_question = None
        current_options = []

        # Process line by line
        lines = [line.strip() for line in generated_text.split('\n') if line.strip()]

        for line in lines:
            if line.startswith('Q:') or line[0].isdigit() and '. ' in line:
                # Save previous question if it exists
                if current_question and len(current_options) == 4:
                    # Get the answers without their numbers
                    answers = [opt.split(':', 1)[1].strip() for opt in current_options]
                    correct_answer = answers[0]  # First one is always correct

                    # Separate the correct answer from the wrong answers
                    wrong_answers = answers[1:]

                    # Shuffle the wrong answers only
                    random.shuffle(wrong_answers)

                    # Insert the correct answer at a random position in the list
                    options = wrong_answers[:]
                    correct_position = random.randint(0, 3)  # Random index from 0 to 3
                    options.insert(correct_position, correct_answer)

                    # Create options with fixed A, B, C, D prefixes
                    formatted_options = [
                        f"A: {options[0]}",
                        f"B: {options[1]}",
                        f"C: {options[2]}",
                        f"D: {options[3]}"
                    ]

                    # Find which position (0-3) has the correct answer
                    correct_letter = 'ABCD'[options.index(correct_answer)]

                    questions.append({
                        'question': current_question,
                        'options': formatted_options,
                        'correct_answer': correct_letter
                    })

                # Start new question
                current_question = line.split(': ', 1)[-1] if ': ' in line else line
                current_options = []

            elif line[0].isdigit() and ':' in line:
                current_options.append(line)

        # Don't forget to add the last question
        if current_question and len(current_options) == 4:
            # Process last question same way
            answers = [opt.split(':', 1)[1].strip() for opt in current_options]
            correct_answer = answers[0]
            wrong_answers = answers[1:]
            random.shuffle(wrong_answers)
            options = wrong_answers[:]
            correct_position = random.randint(0, 3)  # Random index from 0 to 3
            options.insert(correct_position, correct_answer)
            formatted_options = [
                f"A: {options[0]}",
                f"B: {options[1]}",
                f"C: {options[2]}",
                f"D: {options[3]}"
            ]
            correct_letter = 'ABCD'[options.index(correct_answer)]

            questions.append({
                'question': current_question,
                'options': formatted_options,
                'correct_answer': correct_letter
            })

        if not questions:
            raise ValueError("No valid questions were parsed from the response")

        return questions[:num_questions]

    except Exception as e:
        print(f"Error in generate_questions_from_text: {str(e)}")
        raise


@app.route('/')
def home():
    return render_template('index.html')

@app.route('/start')
def start():
    return render_template('start.html')



@app.route('/mcq', methods=['GET', 'POST'])
def mcq():
    if request.method == 'POST':
        try:
            input_text = request.form['input_text']
            num_questions = int(request.form['num_questions'])

            # Validate inputs
            if not input_text.strip():
                return jsonify({'error': 'Please enter some text'}), 400
            
            if num_questions < 1:
                return jsonify({'error': 'Number of questions must be at least 1'}), 400

            # Call the generate function
            questions = generate_questions_from_text(input_text, 'multiple-choice', num_questions)
            
            # Validate questions
            if not questions or len(questions) == 0:
                print("No questions were generated")  # Debug log
                return jsonify({'error': 'No valid questions were generated'}), 500

            print(f"Returning {len(questions)} questions")  # Debug log
            return jsonify({'questions': questions})
            
        except Exception as e:
            print(f"Error in mcq route: {str(e)}")  # Debug log
            return jsonify({'error': str(e)}), 500
            
    return render_template('mcq.html')



@app.route('/true-false', methods=['GET', 'POST'])
def true_false():
    if request.method == 'POST':
        try:
            input_text = request.form['input_text']
            num_questions = int(request.form['num_questions'])

            if not input_text.strip():
                return jsonify({'error': 'Please enter some text'}), 400
            
            if num_questions < 1:
                return jsonify({'error': 'Number of questions must be at least 1'}), 400

            questions = generate_true_false_questions(input_text, num_questions)
            
            if not questions:
                return jsonify({'error': 'No valid questions were generated'}), 500

            return jsonify({'questions': questions})
            
        except Exception as e:
            print(f"Error in true-false route: {str(e)}")
            return jsonify({'error': str(e)}), 500
            
    return render_template('true_false.html')

# Updated Generation Function
def generate_true_false_questions(input_text, num_questions):
    try:
        prompt = f"""Generate exactly {num_questions} true or false questions based on this text: "{input_text}"

        Rules:
        1. Generate EXACTLY {num_questions} questions
        2. Each question must be answerable with True or False
        3. First state the question then the answer
        4. Follow this EXACT format:

        Q: [Question text]
        A: [True/False]"""

        response = co.generate(
            model='command-xlarge-nightly',
            prompt=prompt,
            max_tokens=2000,
            temperature=0.7,
            num_generations=1
        )

        generated_text = response.generations[0].text.strip()
        questions = []
        lines = [line.strip() for line in generated_text.split('\n') if line.strip()]
        
        current_question = None
        
        for line in lines:
            if line.startswith('Q:'):
                current_question = line.split(': ', 1)[-1]
            elif line.startswith('A:'):
                if current_question:
                    answer = line.split(': ', 1)[-1]
                    # Create options and shuffle them
                    options = ['True', 'False']
                    correct_answer = answer.strip()
                    
                    # Shuffle options but track correct index
                    random.shuffle(options)
                    correct_index = options.index(correct_answer)
                    
                    questions.append({
                        'question': current_question,
                        'options': options,
                        'correct_answer': ['A', 'B'][correct_index]
                    })
                    current_question = None

        if not questions:
            raise ValueError("No valid questions were parsed from the response")

        return questions[:num_questions]

    except Exception as e:
        print(f"Error in generate_true_false_questions: {str(e)}")
        raise

@app.route('/generate-questions', methods=['GET', 'POST'])
def questions():
    try:
        if request.method == 'POST':
            # POST request logic
            data = request.get_json()
            input_text = data.get('input_text')
            num_questions = int(data.get('num_questions', 5))

            if not input_text or num_questions < 1:
                return jsonify({'error': 'Invalid input: Please provide text and a valid number of questions.'}), 400

            questions = generate_questions_only(input_text, num_questions)
            if not questions:
                return jsonify({'error': 'Failed to generate questions.'}), 500

            return jsonify({'questions': questions})

        # For GET requests, render the HTML page
        return render_template('questions_generator.html')

    except Exception as e:
        return jsonify({'error': f"An unexpected error occurred: {str(e)}"}), 500


def generate_questions_only(input_text, num_questions):
    try:
        # Prompt for the model with specific instructions for generating questions
        prompt = f"""Generate exactly {num_questions} questions based on this text: "{input_text}"

        Rules:
        1. Create only questions, no answers
        2. Use different question types (who, what, when, why, how)
        3. Make questions specific to the text content
        4. Format each question on a separate line starting with Q:
        
        Example:
        Q: What was the main event described in the text?
        Q: How did the protagonist resolve the conflict?"""

        # External API call to generate questions (Ensure 'co' is correctly instantiated)
        response = co.generate(
            model='command-xlarge-nightly',
            prompt=prompt,
            max_tokens=1000,
            temperature=0.7,
            num_generations=1
        )

        # Extract the generated text
        generated_text = response.generations[0].text.strip()
        
        # Initialize an empty list to hold the generated questions
        questions = []

        # Process the generated text and extract each question
        for line in generated_text.split('\n'):
            line = line.strip()
            if line.startswith('Q:') or line.startswith('Question:'):
                # Clean up question formatting
                question = line.split(': ', 1)[-1].replace('"', '').strip()
                if not question.endswith('?'):
                    question += '?'  # Add a question mark if missing
                questions.append(question)

        # Return the first 'num_questions' questions
        return questions[:num_questions]

    except Exception as e:
        print(f"Error generating questions: {str(e)}")
        raise RuntimeError("Failed to generate questions from the model.")

# Ensure 'co' is properly defined (example, replace with your actual API client initialization)
# co = YourApiClient(api_key='your_api_key')

if __name__ == "__main__":
    app.run(debug=True)

