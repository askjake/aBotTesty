let counter = 0;

const nanoid = () => {
  counter += 1;
  return `test-id-${counter}`;
};

const customAlphabet = () => () => {
  counter += 1;
  return `test-id-${counter}`;
};

module.exports = {
  nanoid,
  customAlphabet,
};
