export const readStream = async (error: ReadableStream): Promise<string> => {
  const data = (await error?.getReader()?.read())?.value;
  // eslint-disable-next-line prefer-spread
  const str = String.fromCharCode.apply(String, data);
  return JSON.parse(str);
};
